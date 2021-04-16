#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import io
import re
import copy
import shutil
import threading
import datetime
import decimal
import xml.parsers.expat
from xml.etree.cElementTree import ElementTree

import pygame

import cw
from cw.util import synclock

import typing
from typing import BinaryIO, Callable, Dict, Generator, ItemsView, Iterable, Iterator, KeysView, List, NoReturn,\
    Optional, Sequence, Set, Tuple, Type, TypeVar, Union

_lock = threading.Lock()

_WSN_DATA_DIRS = ("area", "battle", "package", "castcard", "skillcard", "itemcard", "beastcard", "infocard")


# ------------------------------------------------------------------------------
# システムデータ
# ------------------------------------------------------------------------------

class SystemData(object):
    resource_cache: Dict[Union[str,
                               Tuple[str, str, float, Union[bool, List[bool]]],
                               Tuple[Tuple[int, int], Tuple[int, int, int, int], str,
                                     Tuple[int, int, int, int]],
                               Tuple[str, float, Tuple[int, int], bool, str],
                               Tuple[Type["cw.effectbooster._JpySubImage"], float, bool, str]],
                         Union[pygame.surface.Surface, Tuple[pygame.surface.Surface, float], cw.util.SoundInterface]]
    ex_cache: Dict[str, List[Optional[Union[str, bytes]]]]

    def __init__(self, init: bool = True) -> None:
        """
        引数のゲームの状態遷移の情報によって読み込むxmlを変える。
        """
        if not init:
            return
        cw.cwpy.debug = cw.cwpy.setting.debug
        self.wsn_version = ""
        self.data: Optional[CWPyElement] = None
        self.name = ""
        self.sdata = ""
        self.author = ""
        self.fpath = ""
        self.mtime = 0.0
        self.tempdir = ""
        self.scedir = ""
        self.summarypath = ""
        self._filenum = 0
        self._paused_time = 0.0
        self.startid = 0
        self._r_specialchar = re.compile(r"^font_(.)[.]bmp$")

        self._areas: Dict[int, Tuple[str, str]] = {}
        self._battles: Dict[int, Tuple[str, str]] = {}
        self._packs: Dict[int, Tuple[str, str]] = {}
        self._casts: Dict[int, Tuple[str, str]] = {}
        self._infos: Dict[int, Tuple[str, str]] = {}
        self._items: Dict[int, Tuple[str, str]] = {}
        self._skills: Dict[int, Tuple[str, str]] = {}
        self._beasts: Dict[int, Tuple[str, str]] = {}
        self.sparea_mcards: Dict[int, List[Union[cw.sprite.card.MenuCard, cw.sprite.card.EnemyCard]]] = {}

        cw.cwpy.classicdata = None

        self._init_xmlpaths()
        self._init_sparea_mcards()

        self.is_playing = True
        self.events: Optional[cw.event.EventEngine] = None
        self.playerevents: Optional[cw.event.EventEngine] = None  # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
        self.deletedpaths: Union[YadoDeletedPathSet, Set[str]] = set()
        self.lostadventurers: Set[str] = set()
        self.gossips: Dict[str, bool] = {}
        self.compstamps: Dict[str, bool] = {}
        self.friendcards: List[cw.sprite.card.FriendCard] = []
        self.infocards: List[int] = []
        self.infocard_maxindex = 0
        self._infocard_cache: Dict[int, cw.header.InfoCardHeader] = {}
        self.flags: Dict[str, Flag] = {}
        self.steps: Dict[str, Step] = {}
        self.variants: Dict[str, Variant] = {}
        self.labels: Dict[str, str] = {}
        self.ignorecase_table: Dict[str, str] = {}
        self.notice_infoview = False
        self.infocards_beforeevent: Optional[Set[int]] = None
        self.party_environment_backpack = True
        self.party_environment_gameover = True
        self.party_environment_runaway = True
        self.pre_battleareadata: Optional[Tuple[int, Tuple[str, int, int, int], Tuple[str, int, int, int]]] = None
        self.data_cache: Dict[str, CacheData] = {}
        self.path_cache: Dict[Tuple[str, int, bool, bool], str] = {}
        self.resource_cache = {}
        self.resource_cache_size = 0
        self.autostart_round = False
        self.breakpoints: Set[str] = set()
        self.in_f9 = False
        self.in_endprocess = False
        self.background_image_mtime: Dict[str, Tuple[str, float]] = {}
        self.moved_mcards: Dict[Tuple[str, int], Tuple[int, int, int, int]] = {}
        self.instructions: List[str] = []
        self.specialchars = cw.setting.ResourceTable[str, Tuple[pygame.surface.Surface, bool]]("Resource/Image/Font")

        # イベント終了時まで保持されるJPDC撮影などで上書きされたイメージのキャッシュ
        # [path] = (x1 binary, x2 binary, ..., x16 binary)
        self.ex_cache = {}

        # クリア時のデバッグ情報。デバッグ情報ダイアログ表示で削除
        self.debuglog: Optional[cw.debug.logging.DebugLog] = None
        # デバッグ情報がある事を通知する(0=通知無し,1=点滅あり,2=点滅無し)
        self.notice_debuglog = 0

        # "file.x2.bmp"などのスケーリングされたイメージを読み込むか
        self.can_loaded_scaledimage = True

        # メッセージログ
        self.backlog: List[Union[cw.sprite.bill.Bill, cw.sprite.message.BacklogData]] = []
        # キャンプ中に移動したカードの使用回数の記憶
        self.uselimit_table: Dict[Tuple[cw.sprite.card.PlayerCard, cw.header.CardHeader], int] = {}

        # シナリオごとのブレークポイントを保存する
        if isinstance(cw.cwpy.sdata, ScenarioData):
            cw.cwpy.sdata.save_breakpoints()

        # スキン状態変数の初期化
        self.summary: Optional[CWPyElementTree] = cw.cwpy.setting.skindata
        if self.summary.gettext("Property/VariablesKey", "") != "":
            self._init_flags()
            self._init_steps()
            self._init_variants()
        else:
            self.flags = {}
            self.steps = {}
            self.variants = {}

        # 各段階の互換性マーク(SystemDataでは全て互換性情報無し)
        self.versionhint: List[Optional[Tuple[str, str, bool, bool, bool]]] = [
            None,  # メッセージ表示時の話者(キャストまたはカード)
            None,  # 使用中のカード
            None,  # エリア・バトル・パッケージ
            None,  # シナリオ本体
        ]

        # refresh debugger
        self._init_debugger()

    def _init_flags(self) -> None:
        """
        summary.xmlで定義されているフラグを初期化。
        """
        assert self.summary is not None
        self.flags = init_flags(self.summary, False)

    def _init_steps(self) -> None:
        """
        summary.xmlで定義されているステップを初期化。
        """
        assert self.summary is not None
        self.steps = init_steps(self.summary, False)

    def _init_variants(self) -> None:
        """
        summary.xmlで定義されているコモンを初期化。
        """
        assert self.summary is not None
        self.variants = init_variants(self.summary, False)

    def save_variables(self) -> None:
        """宿ごとにスキンの状態変数値を記憶する。"""
        if not cw.cwpy.ydata:
            return

        fpath = cw.util.join_yadodir("SkinVariables.xml")
        if not os.path.isfile(fpath):
            if not (self.flags or self.steps or self.variants):
                return
            cw.xmlcreater.create_skinvariables(fpath)

        skins, _keytable = get_skinkeys()

        data = yadoxml2etree(fpath)
        assert self.summary is not None
        key = self.summary.gettext("Property/VariablesKey", "")
        e_vars = None
        for e_vars2 in data.getfind(".")[:]:
            assert isinstance(e_vars2, CWPyElement)
            if e_vars2.tag != "Variables":
                continue
            key2 = e_vars2.getattr(".", "key", "")
            if key2 == key:
                e_vars = e_vars2
            if key2 not in skins:
                # すでに存在しないスキンの状態変数の記録は除去しておく
                data.remove(".", e_vars2)
                if e_vars is e_vars2:
                    e_vars = None

        if e_vars is None:
            e_vars = cw.data.make_element("Variables", "", attrs={"key": key})
            data.append(".", e_vars)

        if self.flags or self.steps or self.variants:
            attrs = e_vars.attrib.copy()
            e_vars.clear()
            for name, value in attrs.items():
                e_vars.set(name, value)
            if self.flags:
                e_flag = cw.data.make_element("Flags")
                e_vars.append(e_flag)

                for name, flag in self.flags.items():
                    e = cw.data.make_element("Flag", name, {"value": str(flag.value)})
                    e_flag.append(e)
            if self.steps:
                e_step = cw.data.make_element("Steps")
                e_vars.append(e_step)

                for name, step in self.steps.items():
                    e = cw.data.make_element("Step", name, {"value": str(step.value)})
                    e_step.append(e)
            if self.variants:
                e_variant = cw.data.make_element("Variants")
                e_vars.append(e_variant)

                for name, variant in self.variants.items():
                    # CWPyのデータはテキストと子要素を両立させない構造になっているので
                    # リストか構造体の場合はパスをテキストにするのではなく、<Name>要素を生成するようにする
                    if variant.type in ("List", "Structure"):
                        e = cw.data.make_element("Variant", "")
                        e.append(cw.data.make_element("Name", name))
                        Variant.value_to_element(variant.value, e)
                    else:
                        e = cw.data.make_element("Variant", name)
                        Variant.value_to_element(variant.value, e)
                    e_variant.append(e)
        else:
            data.remove(".", e_vars)
            if len(data.getroot()) == 0:
                # 記憶すべき状態変数値が無くなった
                cw.cwpy.ydata.deletedpaths.add(data.fpath)
                return
        data.is_edited = True
        data.write_xml()
        cw.cwpy.ydata.deletedpaths.discard(data.fpath)

    def load_variables(self) -> None:
        """宿ごとの状態変数値をロードする。"""
        if not cw.cwpy.ydata:
            return
        if not (self.flags or self.steps or self.variants):
            return
        fpath = cw.util.join_yadodir("SkinVariables.xml")
        if not os.path.isfile(fpath):
            return
        data = yadoxml2etree(fpath)
        assert self.summary is not None
        key = self.summary.gettext("Property/VariablesKey", "")
        for e_vars in data.getfind("."):
            assert isinstance(e_vars, CWPyElement)
            if e_vars.tag != "Variables":
                return
            key2 = e_vars.getattr(".", "key", "")
            if key2 == key:
                self._load_variables(e_vars)
                break

    def _load_variables(self, data: Union["CWPyElementTree", "CWPyElement"]) -> None:
        for e in data.getfind("Flags", raiseerror=False):
            if e.text in self.flags:
                self.flags[e.text].value = e.getbool(".", "value")

        for e in data.getfind("Steps", raiseerror=False):
            if e.text in self.steps:
                self.steps[e.text].value = e.getint(".", "value")

        for e in data.getfind("Variants", raiseerror=False):
            e_name = e.find("Name")
            if e_name is None:
                # 値がリスト以外の場合はテキストがそのままパスになっている
                name = e.text
            else:
                # 値がリストか構造体の場合は<Name>要素が存在している
                name = e_name.text
            if name in self.variants:
                v_value = Variant.value_from_element(e)
                self.variants[name].value = v_value

    def reset_variables(self) -> None:
        """すべての状態変数を初期化する。"""
        assert self.summary is not None
        for e in self.summary.getfind("Steps"):
            i_value = e.getint(".", "default")
            name = e.gettext("Name", "")
            self.steps[name].set(i_value)

        for e in self.summary.getfind("Flags"):
            b_value = e.getbool(".", "default")
            name = e.gettext("Name", "")
            self.flags[name].set(b_value)
            self.flags[name].redraw_cards()

        for e in self.summary.getfind("Variants", raiseerror=False):
            v_value = Variant.value_from_element(e, "defaulttype", "defaultvalue")
            name = e.gettext("Name", "")
            self.variants[name].set(v_value)

    def _init_debugger(self) -> None:
        cw.cwpy.event.refresh_variablelist()

    def update_skin(self) -> None:
        self._init_xmlpaths()
        self._init_sparea_mcards()

        self.save_variables()
        self.summary = cw.cwpy.setting.skindata
        if self.summary.gettext("Property/VariablesKey", "") != "":
            self._init_flags()
            self._init_steps()
            self._init_variants()
            self.load_variables()
        else:
            self.flags = {}
            self.steps = {}
            self.variants = {}
        self._init_debugger()

        def func() -> None:
            cw.cwpy.is_debuggerprocessing = False
            if cw.cwpy.is_showingdebugger() and cw.cwpy.event:
                cw.cwpy.event.refresh_tools()
        cw.cwpy.frame.exec_func(func)

    def _init_xmlpaths(self, xmlonly: bool = False) -> None:
        cw.fsync.sync()
        self._areas.clear()
        self._battles.clear()
        self._packs.clear()
        self._casts.clear()
        self._infos.clear()
        self._items.clear()
        self._skills.clear()
        self._beasts.clear()
        dpaths = (cw.util.join_paths(cw.cwpy.skindir, "Resource/Xml", cw.cwpy.status),
                  cw.util.join_paths("Data/SkinBase/Resource/Xml", cw.cwpy.status),
                  cw.util.join_paths(cw.cwpy.skindir, "Resource/Xml/Package"),
                  "Data/SkinBase/Resource/Xml/Package",
                  cw.util.join_paths(cw.cwpy.skindir, "Resource/Xml/Area"),
                  "Data/SkinBase/Resource/Xml/Area")

        for dpath in dpaths:
            if not os.path.isdir(dpath):
                continue
            for fname in os.listdir(dpath):
                path = cw.util.join_paths(dpath, fname)

                if os.path.isfile(path) and fname.lower().endswith(".xml"):
                    e = xml2element(path, "Property")
                    resid = e.getint("Id")
                    name = e.gettext("Name")
                    if os.path.basename(dpath) == "Package":
                        if resid not in self._packs:
                            self._packs[resid] = (name, path)
                    elif os.path.basename(dpath) == "Title" and resid not in cw.AREAS_TITLE:
                        continue
                    elif os.path.basename(dpath) == "Yado" and resid not in cw.AREAS_YADO:
                        continue
                    elif resid not in self._areas:
                        self._areas[resid] = (name, path)

    def update_scenariopath(self, normpath: str, dst: str, dstisfile: bool) -> None:
        if not self.fpath:
            return
        normpath2 = cw.util.get_keypath(self.fpath)
        if normpath != normpath2:
            return

        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.fpath = dst
        if not dstisfile:
            self.tempdir = dst
            self.scedir = dst

        def update_table(table: Dict[int, Tuple[str, str]]) -> None:
            d = table.copy()
            table.clear()
            for resid, (name, path) in d.items():
                rel = cw.util.is_descendant(path=path, start=normpath)
                if rel:
                    path = cw.util.join_paths(dst, rel)
                table[resid] = (name, path)
        update_table(self._areas)
        update_table(self._battles)
        update_table(self._packs)
        update_table(self._casts)
        update_table(self._infos)
        update_table(self._items)
        update_table(self._skills)
        update_table(self._beasts)

        self.data_cache = {}
        self.path_cache = {}
        self.resource_cache = {}
        self.resource_cache_size = 0

    def update_scenariopath2(self, normpath: str, dst: str, dstisfile: bool) -> None:
        if not self.fpath:
            return
        if dstisfile:
            return
        dst = cw.util.get_keypath(dst)
        normpath2 = cw.util.get_keypath(self.fpath)
        if dst != normpath2:
            return
        cw.cwpy.rsrc.specialchars.reset()
        self.update_scale()

    def _init_sparea_mcards(self) -> None:
        """
        カード移動操作エリアのメニューカードを作成する。
        エリア移動時のタイムラグをなくすための操作。
        """
        d = {}

        for key in self._areas.keys():
            if key in cw.AREAS_TRADE:
                data = self.get_mcarddata(key, battlestatus=False)
                areaid = cw.cwpy.areaid
                cw.cwpy.areaid = key
                mcards = cw.cwpy.set_mcards(data, False, addgroup=False, setautospread=False)
                cw.cwpy.areaid = areaid
                d[key] = mcards

        self.sparea_mcards = d

    def is_wsnversion(self, wsn_version: str, cardversion: Optional[str] = None) -> bool:
        if cardversion is None:
            swsnversion = self.wsn_version
        else:
            swsnversion = cardversion

        if not swsnversion:
            return not wsn_version
        else:
            try:
                ivs = int(swsnversion)
                ivd = int(wsn_version)
                return ivd <= ivs
            except Exception:
                return False

    def get_versionhint(self, frompos: int = 0) -> Optional[Tuple[str, str, bool, bool, bool]]:
        """現在有効になっている互換性マークを返す(常に無し)。"""
        return None

    def set_versionhint(self, pos: int, hint: Optional[Tuple[str, str, bool, bool, bool]]) -> None:
        """互換性モードを設定する(処理無し)。"""
        pass

    def update_scale(self) -> None:
        for mcards in self.sparea_mcards.values():
            for mcard in mcards:
                mcard.update_scale()
        for log in self.backlog:
            if isinstance(log, cw.sprite.message.BacklogData) and log.specialchars:
                log.specialchars.reset()

    def sweep_resourcecache(self, size: int) -> None:
        """新しくキャッシュを追加した時にメモリが不足しそうであれば
        これまでのキャッシュをクリアする。
        """
        # 使用可能なヒープサイズの半分までをキャッシュに使用する"
        if sys.platform == "win32":
            import ctypes.wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.wintypes.DWORD),
                    ("dwMemoryLoad", ctypes.wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            ms = MEMORYSTATUSEX()
            ms.dwLength = ctypes.sizeof(ms)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(ms)):
                limit = ms.ullTotalVirtual // 2
            else:
                limit = 1*1024*1024*1024
        else:
            import resource
            limit = resource.getrlimit(resource.RLIMIT_DATA)[0] // 2

        if min(limit, 2*1024*1024*1024) < self.resource_cache_size + size:
            self.resource_cache.clear()
            self.resource_cache_size = 0

        self.resource_cache_size += size

    def find_flag(self, path: str, is_differentscenario: bool, event: Optional["cw.event.Event"]) -> Optional["Flag"]:
        """
        pathが指すフラグを返す。
        eventにローカル変数がある場合は優先する。
        """
        if event and path in event.flags:
            return event.flags[path]
        return self.flags.get(path, None) if not is_differentscenario else None

    def find_step(self, path: str, is_differentscenario: bool, event: Optional["cw.event.Event"]) -> Optional["Step"]:
        """
        pathが指すステップを返す。
        eventにローカル変数がある場合は優先する。
        """
        if event and path in event.steps:
            return event.steps[path]
        return self.steps.get(path, None) if not is_differentscenario else None

    def find_variant(self, path: str, is_differentscenario: bool,
                     event: Optional["cw.event.Event"]) -> Optional["Variant"]:
        """
        pathが指すコモンを返す。
        eventにローカル変数がある場合は優先する。
        """
        if event and path in event.variants:
            return event.variants[path]
        return self.variants.get(path, None) if not is_differentscenario else None

    def get_flagvalue(self, path: str) -> bool:
        """
        フラグの値を返す。
        フラグが存在しない場合はTrueを返す。
        """
        if not path:
            return True
        flag_o = self.flags.get(path, None)
        return bool(flag_o) if flag_o is not None else True

    def start(self) -> None:
        pass

    def end(self, showdebuglog: bool = False, complete: bool = False, failure: bool = False) -> None:
        pass

    def save_breakpoints(self) -> None:
        pass

    def get_totalpyaingtime(self) -> float:
        return 0.0

    def get_pausedtime(self) -> float:
        return 0.0

    def start_timekeeper(self) -> None:
        pass

    def resume_timekeeper(self) -> None:
        pass

    def sleep_timekeeper(self) -> None:
        pass

    def set_log(self, force_create: bool = False) -> Tuple[bool, Optional[Iterable[Tuple[str, int, int, bool, str]]]]:
        """
        wslファイルの読み込みまたは新規作成を行う。
        読み込みを行った場合はTrue、新規作成を行った場合はFalseを返す。
        """
        assert cw.cwpy.ydata
        assert cw.cwpy.ydata.party
        cw.cwpy.set_pcards()
        cw.util.remove(cw.util.join_paths(cw.tempdir, "ScenarioLog"))
        path = cw.util.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"
        path = cw.util.get_yadofilepath(path)

        if path and not force_create:
            cw.util.decompress_zip(path, cw.tempdir, "ScenarioLog")
            musicpaths = self.load_log(cw.util.join_paths(cw.tempdir, "ScenarioLog/ScenarioLog.xml"), False)
            return True, musicpaths
        else:
            self.create_log()
            return False, None

    def create_log(self) -> None:
        pass

    def remove_log(self, debuglog: Optional["cw.debug.logging.DebugLog"]) -> None:
        assert cw.cwpy.ydata
        assert cw.cwpy.ydata.party
        cw.fsync.sync()
        if debuglog:
            dpath = cw.util.join_paths(cw.tempdir, "ScenarioLog/Members")
            for pcard in cw.cwpy.get_pcards():
                fname = os.path.basename(pcard.data.fpath)
                fpath = cw.util.join_paths(dpath, fname)
                prop = cw.header.GetProperty(fpath)
                old_coupons = set()
                get_coupons: List[Tuple[str, int]] = []
                lose_coupons: List[Tuple[str, int]] = []

                for _coupon, attrs, name in prop.third.get("Coupons", []):
                    old_coupons.add(name)
                    value = int(attrs.get("value", "0"))
                    if not pcard.has_coupon(name):
                        lose_coupons.append((name, value))
                for name in pcard.get_coupons():
                    if name not in old_coupons:
                        value_e = pcard.get_couponvalue(name)
                        assert value_e is not None
                        get_coupons.append((name, value_e))
                debuglog.add_player(pcard, get_coupons, lose_coupons)

            dpath = cw.util.join_paths(cw.tempdir, "ScenarioLog/Party")
            for fname in os.listdir(dpath):
                if fname.lower().endswith(".xml"):
                    prop = cw.header.GetProperty(cw.util.join_paths(dpath, fname))
                    money = int(prop.properties.get("Money", str(cw.cwpy.ydata.party.money)))
                    debuglog.set_money(money, cw.cwpy.ydata.party.money)
                    break

            for gossip, get in cw.util.sorted_by_attr(iter(self.gossips.items())):
                debuglog.add_gossip(gossip, get)

            for compstamp, get in cw.util.sorted_by_attr(iter(self.compstamps.items())):
                debuglog.add_compstamp(compstamp, get)

            for ctype in ("SkillCard", "ItemCard", "BeastCard"):
                dname = "Deleted" + ctype
                dpath = cw.util.join_paths(cw.tempdir, "ScenarioLog/Party", dname)
                if os.path.isdir(dpath):
                    for fname in os.listdir(dpath):
                        if fname.lower().endswith(".xml"):
                            fpath = cw.util.join_paths(dpath, fname)
                            prop = cw.header.GetProperty(fpath)
                            name = prop.properties.get("Name", "")
                            desc = cw.util.decodewrap(prop.properties.get("Description", ""))
                            scenario = prop.properties.get("Scenario", "")
                            author = prop.properties.get("Author", "")
                            premium = prop.properties.get("Premium", "Normal")
                            attachment = cw.util.str2bool(prop.properties.get("Attachment", "False"))
                            if ctype != "BeastCard" or attachment:
                                debuglog.add_lostcard(ctype, name, desc, scenario, author, premium)

        cw.util.remove(cw.util.join_paths(cw.tempdir, "ScenarioLog"))
        path = cw.util.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"
        cw.cwpy.ydata.deletedpaths.add(path)

    def load_log(self, path: str, recording: bool) -> List[Tuple[str, int, int, bool, str]]:
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

        return []

    def get_resdata(self, isbattle: bool, resid: int) -> Optional["CWPyElement"]:
        if isbattle:
            data = self.get_battledata(resid)
        else:
            data = self.get_areadata(resid)

        if data is None:
            return None

        return data

    def get_carddata(self, linkdata: "CWPyElement", in_inusecard: bool = True,
                     inusecardheader: Optional["cw.header.CardHeader"] = None) -> Optional["CWPyElement"]:
        return linkdata

    def is_updatedfilenames(self) -> bool:
        """WSNシナリオのデータ(XML)のファイル名がデータテーブル
        作成時点から変更されている場合はTrueを返す。
        """
        return False

    def _get_resdata(self, table: Dict[int, Tuple[str, str]], resid: int, tag: str, nocache: bool, resname: str = "?",
                     rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        fpath0 = table.get(resid, ("", "(未定義の%s ID:%s)" % (resname, resid)))[1]
        fpath = self._get_resfpath(table, resid)
        if fpath is None:
            # イベント中に存在しないリソースを読み込もうとする
            # クラシックシナリオがいくつか確認されているため、
            # 読込失敗の警告ダイアログは出さないようにする。
            # s = u"%s の読込に失敗しました。" % (os.path.basename(fpath0))
            # cw.cwpy.call_modaldlg("ERROR", text=s)
            return None
        try:
            return xml2element(fpath, tag, nocache=nocache, rootattrs=rootattrs)
        except Exception:
            cw.util.print_ex()
            s = "%s の読込に失敗しました。" % (os.path.basename(fpath0))
            cw.cwpy.call_modaldlg("ERROR", text=s)
            return None

    def _get_resname(self, table: Dict[int, Tuple[str, str]], resid: int) -> Optional[str]:
        return table.get(resid, (None, None))[0]

    def _get_resfpath(self, table: Dict[int, Tuple[str, str]], resid: int) -> Optional[str]:
        fpath = table.get(resid, None)
        if fpath is None:
            return None
        if cw.fsync.is_waiting(fpath[1]):
            cw.fsync.sync()
        if not os.path.isfile(fpath[1]) and self.is_updatedfilenames():
            self._init_xmlpaths(xmlonly=True)
            fpath = table.get(resid, None)
            if fpath is None:
                return None
        return fpath[1]

    def _get_resids(self, table: Dict[int, Tuple[str, str]]) -> List[int]:
        return list(table.keys())

    def get_areadata(self, resid: int, tag: str = "", nocache: bool = False,
                     rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        return self._get_resdata(self._areas, resid, tag, nocache, resname="エリア", rootattrs=rootattrs)

    def get_areaname(self, resid: int) -> Optional[str]:
        return self._get_resname(self._areas, resid)

    def get_areafpath(self, resid: int) -> Optional[str]:
        return self._get_resfpath(self._areas, resid)

    def get_areaids(self) -> List[int]:
        return self._get_resids(self._areas)

    def get_battledata(self, resid: int, tag: str = "", nocache: bool = False,
                       rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        return self._get_resdata(self._battles, resid, tag, nocache, resname="バトル", rootattrs=rootattrs)

    def get_battlename(self, resid: int) -> Optional[str]:
        return self._get_resname(self._battles, resid)

    def get_battlefpath(self, resid: int) -> Optional[str]:
        return self._get_resfpath(self._battles, resid)

    def get_battleids(self) -> List[int]:
        return self._get_resids(self._battles)

    def get_packagedata(self, resid: int, tag: str = "", nocache: bool = False,
                        rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        return self._get_resdata(self._packs, resid, tag, nocache, resname="パッケージ", rootattrs=rootattrs)

    def get_packagename(self, resid: int) -> Optional[str]:
        return self._get_resname(self._packs, resid)

    def get_packagefpath(self, resid: int) -> Optional[str]:
        return self._get_resfpath(self._packs, resid)

    def get_packageids(self) -> List[int]:
        return self._get_resids(self._packs)

    def get_castdata(self, resid: int, tag: str = "", nocache: bool = False,
                     rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        return self._get_resdata(self._casts, resid, tag, nocache, resname="キャスト", rootattrs=rootattrs)

    def get_castname(self, resid: int) -> Optional[str]:
        return self._get_resname(self._casts, resid)

    def get_castfpath(self, resid: int) -> Optional[str]:
        return self._get_resfpath(self._casts, resid)

    def get_castids(self) -> List[int]:
        return self._get_resids(self._casts)

    def get_skilldata(self, resid: int, tag: str = "", nocache: bool = False,
                      rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        return self._get_resdata(self._skills, resid, tag, nocache, resname="特殊技能", rootattrs=rootattrs)

    def get_skillname(self, resid: int) -> Optional[str]:
        return self._get_resname(self._skills, resid)

    def get_skillfpath(self, resid: int) -> Optional[str]:
        return self._get_resfpath(self._skills, resid)

    def get_skillids(self) -> List[int]:
        return self._get_resids(self._skills)

    def get_itemdata(self, resid: int, tag: str = "", nocache: bool = False,
                     rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        return self._get_resdata(self._items, resid, tag, nocache, resname="アイテム", rootattrs=rootattrs)

    def get_itemname(self, resid: int) -> Optional[str]:
        return self._get_resname(self._items, resid)

    def get_itemfpath(self, resid: int) -> Optional[str]:
        return self._get_resfpath(self._items, resid)

    def get_itemids(self) -> List[int]:
        return self._get_resids(self._items)

    def get_beastdata(self, resid: int, tag: str = "", nocache: bool = False,
                      rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        return self._get_resdata(self._beasts, resid, tag, nocache, resname="召喚獣", rootattrs=rootattrs)

    def get_beastname(self, resid: int) -> Optional[str]:
        return self._get_resname(self._beasts, resid)

    def get_beastfpath(self, resid: int) -> Optional[str]:
        return self._get_resfpath(self._beasts, resid)

    def get_beastids(self) -> List[int]:
        return self._get_resids(self._beasts)

    def get_infodata(self, resid: int, tag: str = "", nocache: bool = False,
                     rootattrs: Optional[Dict[str, str]] = None) -> Optional["CWPyElement"]:
        return self._get_resdata(self._infos, resid, tag, nocache, resname="情報", rootattrs=rootattrs)

    def get_infoname(self, resid: int) -> Optional[str]:
        return self._get_resname(self._infos, resid)

    def get_infofpath(self, resid: int) -> Optional[str]:
        return self._get_resfpath(self._infos, resid)

    def get_infoids(self) -> List[int]:
        return self._get_resids(self._infos)

    def _get_carddatapath(self, rtype: str, resid: int, dpath: str) -> str:
        cw.fsync.sync()
        dpath = cw.util.join_paths(dpath, rtype)
        if not os.path.isdir(dpath):
            return ""
        for fpath in os.listdir(dpath):
            if not fpath.lower().endswith(".xml"):
                continue
            fpath = cw.util.join_paths(dpath, fpath)
            idstr = cw.header.GetName(fpath, tagname="Id").name
            if not idstr or int(idstr) != resid:
                continue
            return fpath

        return ""

    def copy_carddata(self, linkdata: "CWPyElement", dstdir: str, from_scenario: bool, scedir: str,
                      imgpaths: Dict[str, str]) -> None:
        """参照で指定された召喚獣カードを宿へコピーする。"""
        assert linkdata.tag == "BeastCard"
        resid = linkdata.getint("Property/LinkId", 0)
        if resid == 0:
            return

        if scedir == self.scedir:
            path = self.get_beastfpath(resid)
            if not path or not os.path.isfile(path):
                return
            e_beastdata = self.get_beastdata(resid)
            if e_beastdata is None:
                return
            data = xml2etree(element=e_beastdata)
            dstpath = cw.util.relpath(path, self.tempdir)
        else:
            path = self._get_carddatapath(linkdata.tag, resid, scedir)
            try:
                data = xml2etree(path)
            except Exception:
                cw.util.print_ex()
                return
            dstpath = cw.util.relpath(path, scedir)

        if path in imgpaths:
            return

        assert isinstance(data, CWPyElementTree)
        data = copytree(data, copyall=True)

        dstpath = cw.util.join_paths(dstdir, dstpath)
        imgpaths[path] = dstpath
        can_loaded_scaledimage = data.getbool(".", "scaledimage", False)

        cw.cwpy.copy_materials(data, dstdir, from_scenario=from_scenario, scedir=scedir, imgpaths=imgpaths,
                               can_loaded_scaledimage=can_loaded_scaledimage)
        data.fpath = dstpath
        data.write_xml(True)

    def change_data(self, resid: int, data: Optional["CWPyElement"] = None) -> bool:
        if data is None:
            data = self.get_resdata(cw.cwpy.is_battlestatus(), resid)
        if data is None:
            return False
        self.data = data
        assert self.data is not None

        if isinstance(self, ScenarioData):
            self.set_versionhint(cw.HINT_AREA,
                                 cw.cwpy.sct.from_basehint(self.data.getattr("Property", "versionHint", "")))
        cw.cwpy.event.refresh_areaname()
        self.events = cw.event.EventEngine(self.data.getfind("Events"))
        # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
        self.playerevents = cw.event.EventEngine(self.data.getfind("PlayerCardEvents/Events", False))
        return True

    def start_event(self, keynum: Optional[int] = None, keycodes: Optional[List[str]] = None,
                    redraw: bool = True) -> None:
        assert self.events
        if keycodes is None:
            keycodes = []
        cw.cwpy.statusbar.change(False)
        self.events.start(keynum=keynum, keycodes=keycodes)
        if not cw.cwpy.is_dealing() and not cw.cwpy.battle:
            cw.cwpy.statusbar.change()
            if not (pygame.event.peek(pygame.USEREVENT)):
                cw.cwpy.show_party()
                if redraw:
                    cw.cwpy.disposition_pcards()

    def reload_variables(self) -> None:
        flagvals = {}
        stepvals = {}
        variantvals = {}
        for name, flag in list(self.flags.items()):
            flagvals[name] = flag.value
        for name, step in list(self.steps.items()):
            stepvals[name] = step.value
        for name, variant in list(self.variants.items()):
            variantvals[name] = variant.value
        self._init_flags()
        self._init_steps()
        self._init_variants()
        for name, b_value in list(flagvals.items()):
            if name in self.flags:
                self.flags[name].set(b_value, updatedebugger=False)
        for name, i_value in list(stepvals.items()):
            if name in self.steps:
                self.steps[name].set(i_value, updatedebugger=False)
        for name, v_value in list(variantvals.items()):
            if name in self.variants:
                self.variants[name].set(v_value, updatedebugger=False)

    def get_currentareaname(self) -> str:
        """現在滞在中のエリアの名前を返す"""
        if cw.cwpy.is_battlestatus():
            name = self.get_battlename(cw.cwpy.areaid)
        else:
            name = self.get_areaname(cw.cwpy.areaid)
        if name is None:
            name = "(読込失敗)"
        return name

    def get_bgdata(self, e: Optional[Sequence["CWPyElement"]] = None) -> Sequence["CWPyElement"]:
        """背景のElementのリストを返す。
        e: BgImagesのElement。
        """
        if e is None:
            assert self.data is not None
            e = self.data.find("BgImages")

        if e is not None:
            return e
        else:
            return ()

    def get_mcarddata(self, resid: Optional[int] = None, battlestatus: Optional[bool] = None,
                      data: Optional["CWPyElement"] = None) -> Tuple[str, Iterable["CWPyElement"]]:
        """spreadtypeの値("Custom", "Auto")と
        メニューカードのElementのリストをタプルで返す。
        id: 取得対象のエリア。不指定の場合は現在のエリア。
        """
        if not isinstance(battlestatus, bool):
            battlestatus = cw.cwpy.is_battlestatus()

        if data is None:
            if resid is None:
                assert self.data is not None
                data = self.data
            elif battlestatus:
                e = self.get_battledata(resid)
                if e is None:
                    return ("Custom", ())
                data = e
            else:
                e = self.get_areadata(resid)
                if e is None:
                    return ("Custom", ())
                data = e

        e = data.find("MenuCards")
        if e is None:
            e = data.find("EnemyCards")

        if e is not None:
            stype = e.get("spreadtype", "Auto")
            elements: Iterable[CWPyElement] = e
        else:
            stype = "Custom"
            elements = ()

        return stype, elements

    def get_bgmpaths(self) -> List[str]:
        """現在使用可能なBGMのパスのリストを返す。"""
        cw.fsync.sync()
        seq = []
        dpaths = [cw.util.join_paths(cw.cwpy.skindir, "Bgm"), cw.util.join_paths(cw.cwpy.skindir, "BgmAndSound")]
        for dpath2 in os.listdir("Data/Materials"):
            dpath2 = cw.util.join_paths("Data/Materials", dpath2)
            if os.path.isdir(dpath2):
                dpath3 = cw.util.join_paths(dpath2, "Bgm")
                if os.path.isdir(dpath3):
                    dpaths.append(dpath3)
                dpath3 = cw.util.join_paths(dpath2, "BgmAndSound")
                if os.path.isdir(dpath3):
                    dpaths.append(dpath3)
        for dpath in dpaths:
            for dpath2, _dnames, fnames in os.walk(dpath):
                for fname in fnames:
                    if cw.util.splitext(fname)[1].lower() in (".ogg", ".mp3", ".mid", ".wav"):
                        if dpath2 == dpath:
                            dname = ""
                        else:
                            dname = cw.util.relpath(dpath2, dpath)
                        seq.append(cw.util.join_paths(dname, fname))
        return seq

    def fullrecovery_fcards(self) -> None:
        """同行中のNPCの状態を初期化する。"""
        pass  # stub

    def has_infocards(self) -> bool:
        """情報カードを1枚でも所持しているか。"""
        return any(self.infocards)

    def _tidying_infocards(self) -> None:
        """情報カードの情報を整理する。"""
        nums = [a for a in self.infocards if 0 < a]
        indexes = {}
        for i, num in enumerate(sorted(nums)):
            indexes[num] = i + 1
        self.infocard_maxindex = len(nums)
        for i, num in enumerate(self.infocards):
            self.infocards[i] = indexes[num]

    def get_infocards(self, order: bool) -> List[int]:
        """情報カードのID一覧を返す。
        orderがTrueの場合は入手の逆順に返す。
        """
        if order:
            infotable = []
            for resid, num in enumerate(self.infocards):
                if 0 < num:
                    infotable.append((num, resid))
            return [a[1] for a in reversed(sorted(infotable))]
        else:
            infoseq = []
            for resid, num in enumerate(self.infocards):
                if 0 < num:
                    infoseq.append(resid)
            return infoseq

    def append_infocard(self, resid: int) -> None:
        """情報カードを追加する。"""
        if 0x7fffffff <= self.infocard_maxindex:
            self._tidying_infocards()
        if len(self.infocards) <= resid:
            self.infocards.extend([0] * (resid-len(self.infocards)+1))
        self.infocard_maxindex += 1
        self.infocards[resid] = self.infocard_maxindex

    def remove_infocard(self, resid: int) -> None:
        """情報カードを除去する。"""
        if resid < len(self.infocards):
            self.infocards[resid] = 0

    def has_infocard(self, resid: int) -> bool:
        """情報カードを所持しているか。"""
        return bool(resid < len(self.infocards) and self.infocards[resid])

    def count_infocards(self) -> int:
        """情報カードの所持枚数を返す。"""
        return len(self.infocards) - self.infocards.count(0)

    def get_infocardheaders(self) -> List["cw.header.InfoCardHeader"]:
        """所持する情報カードのInfoCardHeaderを入手の逆順で返す。"""
        headers = []
        for resid in self.get_infocards(order=True):
            if resid in self._infocard_cache:
                header = self._infocard_cache[resid]
                headers.append(header)
            elif resid in self.get_infoids():
                rootattrs: Dict[str, str] = {}
                e = self.get_infodata(resid, "Property", rootattrs=rootattrs)
                if e is None:
                    continue
                header = cw.header.InfoCardHeader(e, cw.util.str2bool(rootattrs.get("scaledimage", "False")))
                self._infocard_cache[resid] = header
                headers.append(header)
        return headers

    def can_gameover(self) -> bool:
        """
        敗北・ゲームオーバーが有効な状態か。
        敗北・ゲームオーバー不可状態でも全員対象消去されていれば有効とする。
        """
        return self.party_environment_gameover or not cw.cwpy.get_pcards()


def get_skinkeys() -> Tuple[Set[str], Dict[str, Tuple[str, str]]]:
    """使用可能なスキンの一覧をVariablesKeyのsetで返す。"""
    skins = set()
    keytable: Dict[str, Tuple[str, str]] = {}
    for name in os.listdir("Data/Skin"):
        path = cw.util.join_paths("Data/Skin", name)
        skinpath = cw.util.join_paths("Data/Skin", name, "Skin.xml")
        if os.path.isdir(path) and os.path.isfile(skinpath):
            try:
                prop = cw.header.GetProperty(skinpath)
                key = prop.properties.get("VariablesKey", "")
                if key == "":
                    continue
                skinname = prop.properties.get("Name", "")
                author = prop.properties.get("Author", "")
                skins.add(key)
                if (key not in keytable) or (skinname, author) < keytable[key]:
                    keytable[key] = (skinname, author)
            except Exception:
                # エラーのあるスキンは無視
                cw.util.print_ex()
    return skins, keytable


# ------------------------------------------------------------------------------
# シナリオデータ
# ------------------------------------------------------------------------------

class ScenarioData(SystemData):

    def __init__(self, header: "cw.header.ScenarioHeader", cardonly: bool = False) -> None:
        assert cw.cwpy.ydata

        self.data: Optional[CWPyElement] = None
        self.is_playing = True
        self.in_f9 = False
        self.in_endprocess = False
        self.background_image_mtime: Dict[str, Tuple[str, float]] = {}
        self.fpath = cw.util.get_linktarget(header.get_fpath())
        self.summarypath = ""  # 概略ファイルのパス。_init_xmlpaths の中で取得
        # シナリオの更新時刻。アーカイブの場合はアーカイブ自体、展開済みの場合は概略ファイルの更新時刻となる
        # 概略ファイル("Summary.xml"や"Summary.wsm")の更新時刻は _init_xmlpaths の中で取得する
        self.mtime = os.path.getmtime(self.fpath) if os.path.isfile(self.fpath) else 0.0
        self.name = header.name
        self.author = header.author
        self.startid = header.startid
        self.can_loaded_scaledimage = True
        if not cardonly:
            cw.cwpy.areaid = self.startid
        if os.path.isfile(self.fpath):
            # zip解凍・解凍したディレクトリを登録
            tempdir = cw.cwpy.ydata.recenthistory.check(self.fpath)
            if tempdir:
                self.tempdir = tempdir
                cw.cwpy.ydata.recenthistory.moveend(self.fpath)
                self._find_summaryintemp()
            else:
                self.tempdir = cw.util.join_paths(cw.tempdir, "Scenario")
                orig_tempdir = self._decompress(False)
                cw.cwpy.ydata.recenthistory.append(self.name, self.fpath, orig_tempdir)
        else:
            # 展開済みシナリオ
            self.tempdir = self.fpath

        if cw.scenariodb.TYPE_CLASSIC == header.type:
            cw.cwpy.classicdata = cw.binary.cwscenario.CWScenario(
                self.tempdir, cw.util.join_paths(cw.tempdir, "OldScenario"), cw.cwpy.setting.skintype,
                materialdir="", image_export=False)

        # 特殊文字の画像パスの集合(正規表現)
        self._r_specialchar = re.compile(r"^font_(.)[.]bmp$")

        # 添付テキストのパス
        self.instructions: List[str] = []

        self._areas: Dict[int, Tuple[str, str]] = {}
        self._battles: Dict[int, Tuple[str, str]] = {}
        self._packs: Dict[int, Tuple[str, str]] = {}
        self._casts: Dict[int, Tuple[str, str]] = {}
        self._infos: Dict[int, Tuple[str, str]] = {}
        self._items: Dict[int, Tuple[str, str]] = {}
        self._skills: Dict[int, Tuple[str, str]] = {}
        self._beasts: Dict[int, Tuple[str, str]] = {}

        # 各種xmlファイルのパスを設定
        self._init_xmlpaths()

        if cardonly:
            return

        # 特殊エリアのメニューカードを作成
        self._init_sparea_mcards()
        # エリアデータ初期化
        self.events: Optional[cw.event.EventEngine] = None
        # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
        self.playerevents: Optional[cw.event.EventEngine] = None
        # シナリオプレイ中に削除されたファイルパスの集合
        self.deletedpaths: Union[YadoDeletedPathSet, Set[str]] = set()
        # ロストした冒険者のXMLファイルパスの集合
        self.lostadventurers: Set[str] = set()
        # シナリオプレイ中に追加・削除した終了印・ゴシップの辞書
        # key: 終了印・ゴシップ名
        # value: Trueなら追加。Falseなら削除。
        self.gossips: Dict[str, bool] = {}
        self.compstamps: Dict[str, bool] = {}
        # FriendCardのリスト
        self.friendcards: List[cw.sprite.card.FriendCard] = []
        # 情報カードのリスト
        # 情報カードの枚数分の配列を確保し、各位置に入手順序を格納する
        self.infocards: List[int] = []
        # 最後に設定した情報カードの入手順
        self.infocard_maxindex = 0
        # InfoCardHeaderのキャッシュ
        self._infocard_cache: Dict[int, cw.header.InfoCardHeader] = {}
        # 情報カードを手に入れてから
        # 情報カードビューを開くまでの間True
        self.notice_infoview = False
        self.infocards_beforeevent = None  # イベント開始前の所持情報カードのset
        # 荷物袋の有効・無効(Wsn.4)
        self.party_environment_backpack = True
        # 敗北・ゲームオーバーの有効・無効(Wsn.5)
        self.party_environment_gameover = True
        # 逃走の有効・無効(Wsn.5)
        # 逃走不可に設定されているバトルからは常に逃走不可であるためこのパラメータは影響しない
        self.party_environment_runaway = True
        # 戦闘エリア移動前のエリアデータ(ID, MusicFullPath, BattleMusicPath)
        self.pre_battleareadata: Optional[Tuple[int, Tuple[str, int, int, int], Tuple[str, int, int, int]]] = None
        # バトル中、自動で行動開始するか
        self.autostart_round = False
        # flag set
        self._init_flags()
        # step set
        self._init_steps()
        # variant set
        self._init_variants()
        # refresh debugger
        self._init_debugger()

        # ロードしたデータファイルのキャッシュ
        self.data_cache: Dict[str, CacheData] = {}
        # パス探索が重いのでキャッシュする
        self.path_cache: Dict[Tuple[str, int, bool, bool], str] = {}
        # ロードしたイメージ等のリソースのキャッシュ
        self.resource_cache = {}
        self.resource_cache_size = 0
        # メッセージログ
        self.backlog: List[Union[cw.sprite.bill.Bill, cw.sprite.message.BacklogData]] = []
        # キャンプ中に移動したカードの使用回数の記憶
        self.uselimit_table: Dict[Tuple[cw.sprite.card.PlayerCard, cw.header.CardHeader], int] = {}
        # カード再配置コンテントで移動されたメニューカード
        self.moved_mcards: Dict[Tuple[str, int], Tuple[int, int, int, int]] = {}

        # イベント終了時まで保持されるJPDC撮影などで上書きされたイメージのキャッシュ
        # [path] = (x1 binary, x2 binary, ..., x16 binary)
        self.ex_cache = {}

        # イベントが任意箇所に到達した時に実行を停止するためのブレークポイント
        self.breakpoints = cw.cwpy.breakpoint_table.get((self.name, self.author), set())

        # クリア時のデバッグ情報。デバッグ情報ダイアログ表示で削除
        self.debuglog: Optional[cw.debug.logging.DebugLog] = None
        self.notice_debuglog = 0

        # 各段階の互換性マーク
        self.versionhint: List[Optional[Tuple[str, str, bool, bool, bool]]] = [
            None,  # メッセージ表示時の話者(キャストまたはカード)
            None,  # 使用中のカード
            None,  # エリア・バトル・パッケージ
            None,  # シナリオ本体
        ]

        if cw.cwpy.classicdata:
            self.versionhint[cw.HINT_SCENARIO] = cw.cwpy.classicdata.versionhint

        # プレイ開始時間
        self._start_datetime: Optional[datetime.datetime] = None
        # 停止時間(秒)
        self._paused_time = 0.0
        # 展開中のファイル数
        self._filenum = 0

        self._init_ignorecase_table()

    def _init_ignorecase_table(self) -> None:
        """
        大文字・小文字を区別しないシステムでリソース内のファイルの
        取得に失敗する事があるので、すべて小文字のパスをキーにして
        真のファイル名へのマッピングをしておく。
        この問題は主に手書きされる'*.jpy1'内で発生する。
        """
        cw.fsync.sync()
        self.ignorecase_table = {}
        if os.path.normcase("A") != "a":
            for dpath, _dnames, fnames in os.walk(self.tempdir):
                for fname in fnames:
                    path = cw.util.join_paths(dpath, fname)
                    if os.path.isfile(path):
                        self.ignorecase_table[path.lower()] = path

    def check_archiveupdated(self, reload: bool) -> None:
        """シナリオが圧縮されており、前回の展開より後に更新されていた
        場合は更新分をアーカイブから再取得する。
        圧縮されていない場合はSummary.xml等の更新をチェックし、
        更新されていればファイルの一覧を再読込する。
        """
        if os.path.isfile(self.fpath):
            mtime = os.path.getmtime(self.fpath)
            if self.mtime != mtime:
                self._decompress(True)
                self.mtime = mtime
                if reload:
                    self._reload()
        else:
            mtime = os.path.getmtime(self.summarypath)
            if self.mtime != mtime:
                self.mtime = mtime
                if reload:
                    self._reload()

    def _decompress(self, overwrite: bool) -> str:
        # 展開を別スレッドで実行し、進捗をステータスバーに表示
        self._progress = False
        self._arcname = os.path.basename(self.fpath)
        self._format = ""
        self._cancel_decompress = False

        def startup(filenum: int) -> None:
            def func() -> None:
                self._filenum = filenum
                self._format = "%%sを展開中... (%%%ds/%%s)" % len(str(self._filenum))
                cw.cwpy.expanding = self._format % (self._arcname, 0, self._filenum)
                cw.cwpy.expanding_max = self._filenum
                cw.cwpy.expanding_min = 0
                cw.cwpy.expanding_cur = 0
                cw.cwpy.statusbar.change()
            cw.cwpy.exec_func(func)

        def progress(cur: int) -> bool:
            if not cw.cwpy.is_runningstatus() or self._cancel_decompress:
                return True  # cancel

            def func() -> None:
                if not cw.cwpy.expanding:
                    return
                cw.cwpy.expanding_cur = cur
                cw.cwpy.expanding = self._format % (self._arcname, cur, self._filenum)
                cw.cwpy.update_groups((cw.cwpy.sbargrp,))
                self._progress = False
            if not self._progress or cur == cw.cwpy.expanding_max:
                self._progress = True
                cw.cwpy.exec_func(func)
            return False

        self._error = None

        thr = None
        try:
            if not self.fpath.lower().endswith(".cab"):
                z = cw.util.zip_file(self.fpath, "r")

            def run_decompress() -> None:
                try:
                    if self.fpath.lower().endswith(".cab"):
                        self.tempdir = cw.util.decompress_cab(self.fpath, self.tempdir,
                                                              startup=startup, progress=progress,
                                                              overwrite=overwrite)
                    else:
                        self.tempdir = cw.util.decompress_zip(self.fpath, self.tempdir,
                                                              startup=startup, progress=progress,
                                                              overwrite=overwrite, z=z)
                except Exception as e:
                    cw.util.print_ex(file=sys.stderr)
                    self._error = e

            cw.cwpy.is_decompressing = True

            thr = threading.Thread(target=run_decompress)
            thr.start()
            while thr.is_alive():
                cw.cwpy.get_eventhandler().run()
                cw.cwpy.wait_frame(1)
                cw.cwpy.input()
            cw.cwpy.get_eventhandler().run()
        except cw.event.EffectBreakError as ex:
            self._cancel_decompress = True
            if thr:
                thr.join()
            raise ex
        except Exception as ex:
            cw.util.print_ex()
            self._error = ex
        finally:
            cw.fsync.sync()
            cw.cwpy.lazy_draw()
            cw.cwpy.is_decompressing = False
            if not cw.cwpy.is_runningstatus():
                raise cw.event.EffectBreakError()
            cw.cwpy.expanding = ""
            cw.cwpy.expanding_max = 100
            cw.cwpy.expanding_min = 0
            cw.cwpy.expanding_cur = 0
            cw.cwpy.statusbar.change(False)

        if self._error:
            # 展開エラー
            raise self._error

        # 展開完了
        orig_tempdir = self.tempdir
        self._find_summaryintemp()
        return orig_tempdir

    def _find_summaryintemp(self) -> None:
        # 展開先のフォルダのサブフォルダ内にシナリオ本体がある場合、
        # self.tempdirをサブフォルダに設定する
        cw.fsync.sync()
        fpath1 = cw.util.join_paths(self.tempdir, "Summary.wsm")
        fpath2 = cw.util.join_paths(self.tempdir, "Summary.xml")
        if not (os.path.isfile(fpath1) or os.path.isfile(fpath2)):
            for dpath, _dnames, fnames in os.walk(self.tempdir):
                if "Summary.wsm" in fnames or "Summary.xml" in fnames:
                    # アーカイヴのサブフォルダにシナリオがある
                    self.tempdir = dpath
                    break
            else:
                # "Summary.wsm"がキャメルケースでない場合、見つからない可能性がある
                for dpath, _dnames, fnames in os.walk(self.tempdir):
                    fnames = [f.lower() for f in fnames]
                    if "summary.wsm" in fnames or "summary.xml" in fnames:
                        # アーカイヴのサブフォルダにシナリオがある
                        self.tempdir = dpath
                        break
            self.tempdir = cw.util.join_paths(self.tempdir)

    def get_versionhint(self, frompos: int = 0) -> Optional[Tuple[str, str, bool, bool, bool]]:
        """現在有効になっている互換性マークを返す。"""
        for i, hint in enumerate(self.versionhint[frompos:]):
            if cw.HINT_AREA <= i + frompos and cw.cwpy.event.in_inusecardevent:
                # 使用時イベント中であればエリア・シナリオの互換性情報は見ない
                break
            if hint:
                return hint
        return None

    def set_versionhint(self, pos: int, hint: Optional[Tuple[str, str, bool, bool, bool]]) -> None:
        """互換性モードを設定する。"""
        last = self.get_versionhint()
        self.versionhint[pos] = hint
        if cw.HINT_AREA <= pos and cw.cwpy.sct.to_basehint(last) != cw.cwpy.sct.to_basehint(self.get_versionhint()):
            cw.cwpy.update_titlebar()

    def get_carddata(self, linkdata: "CWPyElement", in_inusecard: bool = True,
                     inusecardheader: Optional["cw.header.CardHeader"] = None) -> Optional["CWPyElement"]:
        """参照で設定されているデータの実体を取得する。"""
        resid = linkdata.getint("Property/LinkId", 0)
        if resid == 0:
            return linkdata

        if in_inusecard:
            inusecard = inusecardheader if inusecardheader else cw.cwpy.event.get_inusecard()
        else:
            inusecard = None
        if inusecard and (cw.cwpy.event.in_inusecardevent or cw.cwpy.event.in_cardeffectmotion or inusecardheader) and\
                (not inusecard.scenariocard or (inusecard.carddata is not None and
                                                inusecard.carddata.gettext("Property/Materials", ""))):
            assert inusecard.carddata is not None
            # プレイ中のシナリオ外のカードを使用
            mates = inusecard.carddata.gettext("Property/Materials", "")
            if not mates:
                return None

            dpath = cw.util.join_yadodir(mates)
            fpath = self._get_carddatapath(linkdata.tag, resid, dpath)
            if not fpath:
                return None
            data = xml2element(fpath, nocache=True)

        else:
            # プレイ中のシナリオ内のカードを使用
            if linkdata.tag == "SkillCard":
                carddata = self.get_skilldata(resid, nocache=True)
            elif linkdata.tag == "ItemCard":
                carddata = self.get_itemdata(resid, nocache=True)
            elif linkdata.tag == "BeastCard":
                carddata = self.get_beastdata(resid, nocache=True)
            else:
                assert False
            if carddata is None:
                return None
            data = carddata

        ule1 = linkdata.find("Property/UseLimit")
        he1 = linkdata.find("Property/Hold")

        prop2 = data.find_exists("Property")
        ule2 = data.find("Property/UseLimit")
        he2 = data.find("Property/Hold")

        if ule1 is not None and ule2 is not None:
            prop2.remove(ule2)
            prop2.append(ule1)
        if he1 is not None and he2 is not None:
            prop2.remove(he2)
            prop2.append(he1)
        return data

    def save_breakpoints(self) -> None:
        key = (self.name, self.author)
        if self.breakpoints:
            cw.cwpy.breakpoint_table[key] = self.breakpoints
        elif key in cw.cwpy.breakpoint_table:
            del cw.cwpy.breakpoint_table[key]

    def get_startdatetime(self) -> Optional[datetime.datetime]:
        return self._start_datetime

    def get_totalpyaingtime(self) -> float:
        if self._start_datetime is None:
            return 0.0
        return (datetime.datetime.today()-self._start_datetime).total_seconds() - self._paused_time

    def get_pausedtime(self) -> float:
        return self._paused_time

    def start_timekeeper(self) -> None:
        if not cw.cwpy.setting.enabled_timekeeper:
            return
        if not (cw.cwpy.ydata and cw.cwpy.ydata.party):
            return

        dpath = os.path.dirname(cw.cwpy.ydata.party.path)
        if not dpath.lower().startswith("yado"):
            dpath = dpath.replace(cw.cwpy.tempdir, cw.cwpy.yadodir, 1)
        dpath = cw.util.join_paths(dpath, "Debug")
        fpath = cw.util.join_paths(dpath, "Timekeeper.xml")
        if cw.fsync.is_waiting(fpath):
            cw.fsync.sync()
        if os.path.isfile(fpath):
            # タイムキーパーはセーブ・ロードしても時間計測を継続するが、
            # シナリオA内でセーブしてからクリアし、シナリオBを開始した
            # というような場合に計測結果がおかしくなるのを避けるため、
            # 次にロードした時にTimekeeper.xmlをロールバックできるように
            # コピーしておく。
            # セーブ操作が行われた時は、ロールバックは不要になるため、
            # OldTimekeeper.xmlを削除する。
            dst = cw.util.join_paths(dpath, "OldTimekeeper.xml")
            if cw.fsync.is_waiting(dst):
                cw.fsync.sync()
            if not os.path.isfile(dst):
                shutil.move(fpath, dst)
        self.resume_timekeeper()

    def resume_timekeeper(self) -> None:
        if not cw.cwpy.setting.enabled_timekeeper:
            return
        if not (cw.cwpy.ydata and cw.cwpy.ydata.party):
            return

        if self._start_datetime is not None:
            return

        dpath = os.path.dirname(cw.cwpy.ydata.party.path)
        if not dpath.lower().startswith("yado"):
            dpath = dpath.replace(cw.cwpy.tempdir, cw.cwpy.yadodir, 1)
        dpath = cw.util.join_paths(dpath, "Debug")
        fpath = cw.util.join_paths(dpath, "Timekeeper.xml")
        if cw.fsync.is_waiting(fpath):
            cw.fsync.sync()
        if os.path.isfile(fpath):
            # 休止からの再開(休止時間を加算)
            try:
                etree = xml2etree(fpath)
                spath = etree.getattr(".", "wsnpath")
                if spath != self.fpath:
                    self._start_datetime = datetime.datetime.today()
                    self._paused_time = 0
                    return

                def parse_datetime(tag: str) -> datetime.datetime:
                    year = etree.getint(tag, "year")
                    month = etree.getint(tag, "month")
                    day = etree.getint(tag, "day")
                    hour = etree.getint(tag, "hour")
                    minute = etree.getint(tag, "minute")
                    second = etree.getint(tag, "second")
                    return datetime.datetime(year, month, day, hour, minute, second)
                self._start_datetime = parse_datetime("StartTime")

                date = datetime.datetime.today()
                paused = etree.getint("PauseTime")
                self._paused_time = paused + (date-parse_datetime("PauseTime")).total_seconds()

            except Exception:
                cw.util.print_ex(file=sys.stderr)
                self._start_datetime = datetime.datetime.today()
                self._paused_time = 0.0
            finally:
                cw.util.remove(fpath)
                cw.util.remove_emptydir(dpath)
        else:
            self._start_datetime = datetime.datetime.today()
            self._paused_time = 0.0

    def sleep_timekeeper(self) -> None:
        if not cw.cwpy.setting.enabled_timekeeper:
            return
        if not (cw.cwpy.ydata and cw.cwpy.ydata.party):
            return

        if self._start_datetime is None:
            return

        dpath = os.path.dirname(cw.cwpy.ydata.party.path)
        if not dpath.lower().startswith("yado"):
            dpath = dpath.replace(cw.cwpy.tempdir, cw.cwpy.yadodir, 1)
        dpath = cw.util.join_paths(dpath, "Debug")
        fpath = cw.util.join_paths(dpath, "Timekeeper.xml")
        if cw.fsync.is_waiting(fpath):
            cw.fsync.sync()
        if os.path.isfile(fpath):
            cw.util.remove(fpath)
            cw.util.remove_emptydir(dpath)
            return

        element = cw.data.make_element("Timekeeper", attrs={"wsnpath": self.fpath})
        date = self._start_datetime
        self._start_datetime = None
        year = date.strftime("%Y")
        month = date.strftime("%m")
        day = date.strftime("%d")
        hour = date.strftime("%H")
        minute = date.strftime("%M")
        second = date.strftime("%S")
        e = cw.data.make_element("StartTime",
                                 attrs={"year": str(year),
                                        "month": str(month),
                                        "day": str(day),
                                        "hour": str(hour),
                                        "minute": str(minute),
                                        "second": str(second),
                                        "paused": str(self._paused_time)})
        element.append(e)

        date2 = datetime.datetime.today()
        year = date2.strftime("%Y")
        month = date2.strftime("%m")
        day = date2.strftime("%d")
        hour = date2.strftime("%H")
        minute = date2.strftime("%M")
        second = date2.strftime("%S")
        e = cw.data.make_element("PauseTime", str(self._paused_time),
                                 attrs={"year": str(year),
                                        "month": str(month),
                                        "day": str(day),
                                        "hour": str(hour),
                                        "minute": str(minute),
                                        "second": str(second)})
        element.append(e)

        etree = cw.data.xml2etree(element=element)
        etree.write_file(fpath)
        cw.cwpy.ydata.deletedpaths.discard(fpath)

    def change_data(self, resid: int, data: Optional["CWPyElement"] = None) -> bool:
        if data is None:
            self.check_archiveupdated(True)
        return SystemData.change_data(self, resid, data=data)

    def reload(self) -> None:
        self.check_archiveupdated(False)
        self._reload()

    def save_variables(self) -> None:
        pass

    def load_variables(self) -> None:
        pass

    def update_skin(self) -> None:
        self._init_xmlpaths()
        self._init_sparea_mcards()
        self._init_debugger()

        def func() -> None:
            cw.cwpy.is_debuggerprocessing = False
            if cw.cwpy.is_showingdebugger() and cw.cwpy.event:
                cw.cwpy.event.refresh_tools()
        cw.cwpy.frame.exec_func(func)

    def _reload(self) -> None:
        self.reload_variables()

        self.data_cache = {}
        self.path_cache = {}
        self.resource_cache = {}
        self.resource_cache_size = 0
        self._init_xmlpaths()

        self._init_ignorecase_table()
        self._init_debugger()

        def func() -> None:
            cw.cwpy.is_debuggerprocessing = False
            if cw.cwpy.is_showingdebugger() and cw.cwpy.event:
                cw.cwpy.event.refresh_tools()
        cw.cwpy.frame.exec_func(func)

    def is_updatedfilenames(self) -> bool:
        """WSNシナリオのデータ(XML)のファイル名がデータテーブル
        作成時点から変更されている場合はTrueを返す。
        """
        datafilenames = set()
        cw.fsync.sync()

        for dpath, _dnames, fnames in os.walk(self.tempdir):
            if not os.path.basename(dpath).lower() in _WSN_DATA_DIRS:
                continue
            for fname in fnames:
                if not fname.lower().endswith(".xml"):
                    continue
                path = cw.util.join_paths(dpath, fname)
                if not os.path.isfile(path):
                    continue
                path = os.path.normcase(path)
                if path not in self._datafilenames:
                    return True
                datafilenames.add(path)

        return datafilenames != self._datafilenames

    def _init_xmlpaths(self, xmlonly: bool = False) -> None:
        """
        シナリオで使用されるXMLファイルのパスを辞書登録。
        また、"Summary.xml"のあるフォルダをシナリオディレクトリに設定する。
        """
        if not xmlonly:
            # 解凍したシナリオのディレクトリ
            self.scedir = ""
            # summary(CWPyElementTree)
            self.summary = None

        cw.fsync.sync()

        # 各xmlの(name, path)の辞書(IDがkey)
        self._datafilenames = set()

        self._areas.clear()
        self._battles.clear()
        self._packs.clear()
        self._casts.clear()
        self._infos.clear()
        self._items.clear()
        self._skills.clear()
        self._beasts.clear()
        self.instructions = []

        re_area = re.compile(r"\Aarea\d+\.wid\Z")
        re_battle = re.compile(r"\Abattle\d+\.wid\Z")
        re_package = re.compile(r"\Apackage\d+\.wid\Z")
        re_mate = re.compile(r"\Amate\d+\.wid\Z")
        re_info = re.compile(r"\Ainfo\d+\.wid\Z")
        re_item = re.compile(r"\Aitem\d+\.wid\Z")
        re_skill = re.compile(r"\Askill\d+\.wid\Z")
        re_beast = re.compile(r"\Abeast\d+\.wid\Z")
        for dpath, _dnames, fnames in os.walk(self.tempdir):
            isdatadir = os.path.basename(dpath).lower() in _WSN_DATA_DIRS
            if xmlonly and not isdatadir:
                continue
            for fname in fnames:
                lf = fname.lower()
                if lf.endswith(".txt"):
                    self.instructions.append(cw.util.join_paths(dpath, fname))

                if xmlonly and not lf.endswith(".xml"):
                    continue

                # "font_*.*"のファイルパスの画像を特殊文字に指定
                if self.eat_spchar(dpath, fname, self.can_loaded_scaledimage):
                    continue
                else:
                    if not (lf.endswith(".xml") or lf.endswith(".wsm") or lf.endswith(".wid")):
                        # シナリオファイル以外はここで処理終わり
                        continue
                    if (lf.endswith(".wsm") or lf.endswith(".wid")) and dpath != self.tempdir:
                        # クラシックなシナリオはディレクトリ直下のみ読み込む
                        continue

                path = cw.util.join_paths(dpath, fname)
                if not os.path.isfile(path):
                    continue
                if lf.endswith(".xml"):
                    self._datafilenames.add(os.path.normcase(path))

                if (lf == "summary.xml" or lf == "summary.wsm") and not self.summary:
                    self.scedir = dpath.replace("\\", "/")
                    self.summarypath = path
                    if os.path.isdir(self.fpath):
                        self.mtime = os.path.getmtime(self.summarypath)
                    self.summary = xml2etree(path)
                    self.can_loaded_scaledimage = self.summary.getbool(".", "scaledimage", False)
                    continue

                if isdatadir and lf.endswith(".xml"):
                    # wsnシナリオの基本要素一覧情報
                    e = xml2element(path, "Property")
                    resid = e.getint("Id", -1)
                    name = e.gettext("Name", "")
                else:
                    if not lf.endswith(".wid"):
                        continue
                    if not cw.cwpy.classicdata:
                        continue
                    # クラシックなシナリオの基本要素一覧情報
                    wdata, _filedata = cw.cwpy.classicdata.load_file(path, nameonly=True)
                    if wdata is None:
                        continue
                    resid = wdata.id
                    name = wdata.name

                reldpath = cw.util.relpath(dpath, self.tempdir)
                ldpath = os.path.basename(reldpath).lower() if reldpath not in ("", ".") else ""
                lbasename = os.path.basename(lf)
                if (ldpath == "area" and lf.endswith(".xml")) or (ldpath == "" and re_area.match(lbasename)):
                    self._areas[resid] = (name, path)
                elif (ldpath == "battle" and lf.endswith(".xml")) or (ldpath == "" and re_battle.match(lbasename)):
                    self._battles[resid] = (name, path)
                elif (ldpath == "package" and lf.endswith(".xml")) or (ldpath == "" and re_package.match(lbasename)):
                    self._packs[resid] = (name, path)
                elif (ldpath == "castcard" and lf.endswith(".xml")) or (ldpath == "" and re_mate.match(lbasename)):
                    self._casts[resid] = (name, path)
                elif (ldpath == "infocard" and lf.endswith(".xml")) or (ldpath == "" and re_info.match(lbasename)):
                    self._infos[resid] = (name, path)
                elif (ldpath == "itemcard" and lf.endswith(".xml")) or (ldpath == "" and re_item.match(lbasename)):
                    self._items[resid] = (name, path)
                elif (ldpath == "skillcard" and lf.endswith(".xml")) or (ldpath == "" and re_skill.match(lbasename)):
                    self._skills[resid] = (name, path)
                elif (ldpath == "beastcard" and lf.endswith(".xml")) or (ldpath == "" and re_beast.match(lbasename)):
                    self._beasts[resid] = (name, path)

        self.specialchars = cw.cwpy.rsrc.specialchars.copy()

        if not xmlonly and not self.summary:
            raise ValueError("Summary file is not found.")

        # 特殊エリアのxmlファイルのパスを設定
        dpath = cw.util.join_paths(cw.cwpy.skindir, "Resource/Xml/Scenario")

        cw.fsync.sync()
        for fname in os.listdir(dpath):
            path = cw.util.join_paths(dpath, fname)

            if os.path.isfile(path) and fname.lower().endswith(".xml"):
                e = xml2element(path, "Property")
                resid = e.getint("Id")
                name = e.gettext("Name")
                self._areas[resid] = (name, path)

        assert self.summary is not None
        # WSNバージョン
        self.wsn_version = self.summary.getattr(".", "dataVersion", "")

    def update_scale(self) -> None:
        # 特殊文字の画像パスの集合(正規表現)
        SystemData.update_scale(self)

        cw.fsync.sync()
        for dpath, _dnames, fnames in os.walk(self.tempdir):
            for fname in fnames:
                if os.path.isfile(cw.util.join_paths(dpath, fname)):
                    self.eat_spchar(dpath, fname, self.can_loaded_scaledimage)
        self.specialchars = cw.cwpy.rsrc.specialchars.copy()

    def eat_spchar(self, dpath: str, fname: str, can_loaded_scaledimage: bool) -> bool:
        # "font_*.*"のファイルパスの画像を特殊文字に指定
        m = self._r_specialchar.match(fname.lower())
        if m:
            def load(dpath: str, fname: str) -> Tuple[pygame.surface.Surface, bool]:
                path = cw.util.get_materialpath(fname, cw.M_IMG, scedir=dpath, findskin=False)
                image = cw.util.load_image(path, True, can_loaded_scaledimage=can_loaded_scaledimage)
                return image, True
            name = "#%s" % (m.group(1))
            cw.cwpy.rsrc.specialchars.set(name, load, dpath, fname)
            cw.cwpy.rsrc.specialchars_is_changed = True
            return True

        else:
            return False

    def start(self) -> None:
        """
        シナリオの開始時の共通処理をまとめたもの。
        荷物袋のカード画像の更新を行う。
        """
        assert cw.cwpy.ydata
        assert cw.cwpy.ydata.party

        self.is_playing = True

        for header in cw.cwpy.ydata.party.get_allcardheaders():
            header.set_scenariostart()

    def end(self, showdebuglog: bool = False, complete: bool = False, failure: bool = False) -> None:
        """
        シナリオの正規終了時の共通処理をまとめたもの。
        冒険の中断時やF9時には呼ばない。
        """
        assert cw.cwpy.ydata
        assert cw.cwpy.ydata.party

        showdebuglog &= cw.cwpy.setting.show_debuglogdialog
        debuglog = None
        if showdebuglog:
            debuglog = cw.debug.logging.DebugLog(self.name)

        if debuglog:
            for fcard in cw.cwpy.get_fcards():
                debuglog.add_friend(fcard)

        if not failure:
            # NPCの連れ込み
            cw.cwpy.ydata.join_npcs()

        self.is_playing = False

        cw.cwpy.ydata.party.set_lastscenario([], "")

        # ロストした冒険者を削除
        for path in self.lostadventurers:
            if not path.lower().startswith("yado"):
                path = cw.util.join_yadodir(path)
            ccard = cw.character.Character(yadoxml2etree(path))
            ccard.remove_numbercoupon()
            if debuglog:
                debuglog.add_lostplayer(ccard)

            # "＿消滅予約"を持ってない場合、アルバムに残す
            if not ccard.has_coupon("＿消滅予約"):
                path = cw.xmlcreater.create_albumpage(ccard.data.fpath, True)
                cw.cwpy.ydata.add_album(path)

            for partyrecord in cw.cwpy.ydata.partyrecord:
                partyrecord.vanish_member(path)
            cw.cwpy.remove_xml(ccard.data.fpath)

        cw.cwpy.ydata.remove_emptypartyrecord()

        # シナリオ取得カードの正規取得処理などを行う
        if cw.cwpy.ydata.party:
            for header in cw.cwpy.ydata.party.get_allcardheaders():
                if debuglog and header.scenariocard:
                    debuglog.add_gotcard(header.type, header.name, header.desc, header.scenario, header.author,
                                         header.premium)
                header.set_scenarioend()

            # 移動済みの荷物袋カードを削除
            for header in cw.cwpy.ydata.party.backpack_moved:
                if header.moved == 2:
                    # 素材も含めて完全削除
                    if debuglog and not header.scenariocard:
                        debuglog.add_lostcard(header.type, header.name, header.desc, header.scenario, header.author,
                                              header.premium)
                    cw.cwpy.remove_xml(header)
                else:
                    # どこかで所有しているので素材は消さない
                    cw.cwpy.ydata.deletedpaths.add(header.fpath)
            cw.cwpy.ydata.party.backpack_moved = []

        # 保存済みJPDCイメージを宿フォルダへ移動
        cw.header.SavedJPDCImageHeader.create_header(debuglog)

        # 状態変数を保存
        cw.cwpy.ydata.save_variables(self.name, self.author, complete,
                                     self.flags, self.steps, self.variants,
                                     debuglog)

        cw.cwpy.background.clear_background()
        self.remove_log(debuglog)
        cw.cwpy.ydata.deletedpaths.update(self.deletedpaths)

        if debuglog:
            startdatetime = self.get_startdatetime()
            pausedtime = self.get_pausedtime()
            self.sleep_timekeeper()
            debuglog.set_times(startdatetime, pausedtime)

        self.debuglog = debuglog
        cw.cwpy.ydata.party.remove_numbercoupon()
        cw.fsync.sync()

    def f9(self) -> None:
        """
        シナリオ強制終了。俗に言うファッ○ユー。
        """
        self.in_f9 = True
        cw.cwpy.exec_func(cw.cwpy.f9)

    def create_log(self) -> None:
        assert cw.cwpy.ydata
        assert cw.cwpy.ydata.party

        # play log
        cw.cwpy.advlog.start_scenario()

        # log
        cw.xmlcreater.create_scenariolog(self, cw.util.join_paths(cw.tempdir, "ScenarioLog/ScenarioLog.xml"), False,
                                         cw.cwpy.advlog.logfilepath)
        # Party and members xml update
        cw.cwpy.ydata.party.write()
        # party
        os.makedirs(cw.util.join_paths(cw.tempdir, "ScenarioLog/Party"))
        path = cw.util.get_yadofilepath(cw.cwpy.ydata.party.data.fpath)
        dstpath = cw.util.join_paths(cw.tempdir, "ScenarioLog/Party",
                                     os.path.basename(path))
        shutil.copy2(path, dstpath)
        # member
        os.makedirs(cw.util.join_paths(cw.tempdir, "ScenarioLog/Members"))

        for data in cw.cwpy.ydata.party.members:
            path = cw.util.get_yadofilepath(data.fpath)
            dstpath = cw.util.join_paths(cw.tempdir, "ScenarioLog/Members",
                                         os.path.basename(path))
            shutil.copy2(path, dstpath)

        # 荷物袋内のカード群(ファイルパスのみ)
        element = cw.data.make_element("BackpackFiles")
        yadodir = cw.cwpy.ydata.party.get_yadodir()
        tempdir = cw.cwpy.ydata.party.get_tempdir()
        backpack = cw.cwpy.ydata.party.backpack[:]
        cw.util.sort_by_attr(backpack, "order")
        for header in backpack:
            if header.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(header.fpath, yadodir)
            else:
                fpath = cw.util.relpath(header.fpath, tempdir)
            fpath = cw.util.join_paths(fpath)
            element.append(cw.data.make_element("File", fpath))
        path = cw.util.join_paths(cw.tempdir, "ScenarioLog/Backpack.xml")
        etree = cw.data.xml2etree(element=element)
        etree.write_file(path)

        # JPDCイメージ
        dpath1 = cw.util.join_paths(cw.tempdir, "ScenarioLog/TempFile")
        key = (self.name, self.author)
        savedjpdcimageheader = cw.cwpy.ydata.savedjpdcimage.get(key, None)
        if savedjpdcimageheader:
            dpath2 = cw.util.join_paths(cw.cwpy.tempdir, "SavedJPDCImage", savedjpdcimageheader.dpath)
            for fpath in savedjpdcimageheader.fpaths:
                frompath = cw.util.join_paths(dpath2, "Materials", fpath)
                frompath = cw.util.get_yadofilepath(frompath)
                if not frompath:
                    continue
                topath = cw.util.join_paths(dpath1, fpath)
                dpath3 = os.path.dirname(topath)
                if not os.path.isdir(dpath3):
                    os.makedirs(dpath3)
                shutil.copy2(frompath, topath)

        # 宿に保存された状態変数(Wsn.4)
        key = (self.name, self.author)
        variables = cw.cwpy.ydata.saved_variables.get(key, None)
        if variables:
            _, flags, steps, variants = variables
            for name, b_value in flags.items():
                flag = self.flags.get(name, None)
                if flag is not None and flag.initialization not in ("Leave"):
                    flag.set(b_value)
            for name, i_value in steps.items():
                step = self.steps.get(name, None)
                if step is not None and step.initialization not in ("Leave"):
                    step.set(i_value)
            for name, v_value in variants.items():
                variant = self.variants.get(name, None)
                if variant is not None and variant.initialization not in ("Leave"):
                    variant.set(v_value)

        # create_zip
        path = cw.util.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"

        if path.startswith(cw.cwpy.yadodir):
            path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)

        cw.util.compress_zip(cw.util.join_paths(cw.tempdir, "ScenarioLog"), path, unicodefilename=True)
        cw.cwpy.ydata.deletedpaths.discard(path)

    def load_log(self, path: str, recording: bool) -> List[Tuple[str, int, int, bool, str]]:
        etree = xml2etree(path)
        # if not recording:
        #     cw.cwpy.debug = etree.getbool("Property/Debug")

        #     if not cw.cwpy.debug == cw.cwpy.setting.debug:
        #         cw.cwpy.statusbar.change()

        #         if not cw.cwpy.debug and cw.cwpy.is_showingdebugger():
        #             cw.cwpy.frame.exec_func(cw.cwpy.frame.close_debugger)
        self.autostart_round = etree.getbool("Property/RoundAutoStart", False)
        self.notice_infoview = etree.getbool("Property/NoticeInfoView", False)
        self.party_environment_backpack = etree.gettext("Property/PartyEnvironment/Backpack", "Enable") != "Disable"
        self.party_environment_gameover = etree.gettext("Property/PartyEnvironment/GameOver", "Enable") != "Disable"
        self.party_environment_runaway = etree.gettext("Property/PartyEnvironment/RunAway", "Enable") != "Disable"
        cw.cwpy.statusbar.loading = True

        self._load_variables(etree)

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
        self.infocard_maxindex = 0
        for e in reversed(etree.getfind("InfoCards")):
            resid = int(e.text)
            if resid in self.get_infoids():
                self.append_infocard(resid)

        self.friendcards = []
        for e in etree.getfind("CastCards"):
            if e.tag == "FriendCard":
                # IDのみ。変換直後の宿でこの状態になる
                e_fcard = self.get_castdata(int(e.text), nocache=True)
                if e_fcard is not None:
                    fcard = cw.sprite.card.FriendCard(data=e_fcard)
                    self.friendcards.append(fcard)
            else:
                fcard = cw.sprite.card.FriendCard(data=e)
                self.friendcards.append(fcard)

        if not recording:
            for e in etree.getfind("DeletedFiles"):
                self.deletedpaths.add(e.text)

            for e in etree.getfind("LostAdventurers"):
                self.lostadventurers.add(e.text)

        e = etree.find_exists("BgImages")
        elements = cw.cwpy.sdata.get_bgdata(e)
        ttype = ("Default", "Default")
        cw.cwpy.background.load(elements, False, ttype, bginhrt=False, nocheckvisible=True)

        e_movedcards = etree.find("MovedCards")
        self.moved_mcards = {}
        if e_movedcards is not None:
            for e in e_movedcards:
                assert isinstance(e, CWPyElement)
                cardgroup = e.getattr(".", "cardgroup", "")
                index = e.getint(".", "index", -1)
                if cardgroup == "" or index == -1:
                    continue
                x = e.getint("Location", "left", 0)
                y = e.getint("Location", "top", 0)
                scale = e.getint("Size", "scale", -1)
                layer = e.getint("Layer", -1)
                layer = cw.util.numwrap(layer, -1, cw.LAYER_MAX)
                self.moved_mcards[(cardgroup, index)] = (x, y, scale, layer)

        self.startid = cw.cwpy.areaid = etree.getint("Property/AreaId")

        logfilepath = etree.gettext("Property/LogFile", "")
        cw.cwpy.advlog.resume_scenario(logfilepath)

        musicpaths = []
        for music in cw.cwpy.music:
            musicpaths.append((music.path, music.subvolume, music.loopcount, music.inusecard, music.fpath))

        e_mpaths = etree.find("Property/MusicPaths")
        if e_mpaths is not None:
            for i, e in enumerate(e_mpaths):
                channel = e.getint(".", "channel", i)
                path = e.text if e.text else ""
                subvolume = e.getint(".", "volume", 100)
                loopcount = e.getint(".", "loopcount", 0)
                inusecard = e.getbool(".", "inusecard", False)
                fullpath = e.getattr(".", "path", "")
                if 0 <= channel and channel < len(musicpaths):
                    musicpaths[channel] = (path, subvolume, loopcount, inusecard, fullpath)
        else:
            # BGMが1CHのみだった頃の互換性維持
            e_music = etree.find("Property/MusicPath")
            if e_music is not None:
                channel = e_music.getint(".", "channel", 0)
                path = e_music.text if e_music.text else ""
                subvolume = e_music.getint(".", "volume", 100)
                loopcount = e_music.getint(".", "loopcount", 0)
                inusecard = e_music.getbool(".", "inusecard", False)
                fullpath = e_music.getattr(".", "path", "")
                if 0 <= channel and channel < len(musicpaths):
                    musicpaths[channel] = (path, subvolume, loopcount, inusecard, fullpath)

        cw.fsync.sync()
        return musicpaths

    def update_log(self) -> None:
        assert cw.cwpy.ydata
        assert cw.cwpy.ydata.party
        cw.xmlcreater.create_scenariolog(self, cw.util.join_paths(cw.tempdir, "ScenarioLog/ScenarioLog.xml"), False,
                                         cw.cwpy.advlog.logfilepath)
        cw.cwpy.advlog.end_scenario(False, False)

        path = cw.util.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"

        if path.startswith("Yado"):
            path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)

        cw.util.compress_zip(cw.util.join_paths(cw.tempdir, "ScenarioLog"), path, unicodefilename=True)

    def get_bgmpaths(self) -> List[str]:
        """現在使用可能なBGMのパスのリストを返す。"""
        cw.fsync.sync()
        seq = SystemData.get_bgmpaths(self)
        dpath = self.tempdir
        for dpath2, _dnames, fnames in os.walk(dpath):
            for fname in fnames:
                if cw.util.splitext(fname)[1].lower() in (".ogg", ".mp3", ".mid", ".wav"):
                    if dpath2 == dpath:
                        dname = ""
                    else:
                        dname = cw.util.relpath(dpath2, dpath)
                    seq.append(cw.util.join_paths(dname, fname))
        return seq

    def fullrecovery_fcards(self) -> None:
        """同行中のNPCを回復する。"""
        seq = []
        for fcard in self.friendcards:
            last = self.get_versionhint(cw.HINT_MESSAGE)
            self.set_versionhint(cw.HINT_MESSAGE, fcard.versionhint)
            # 互換動作: 1.28以前は戦闘毎に同行キャストの状態が完全に復元される
            if cw.cwpy.sct.lessthan("1.28", self.get_versionhint(cw.HINT_MESSAGE)):
                e = cw.cwpy.sdata.get_castdata(fcard.id, nocache=True)
                if e is not None:
                    fcard = cw.sprite.card.FriendCard(data=e)
            else:
                fcard.set_fullrecovery()
                fcard.update_image()
            seq.append(fcard)
            self.set_versionhint(cw.HINT_MESSAGE, last)
        self.friendcards = seq


def init_flags(data: Union["CWPyElementTree", "CWPyElement"], writable: bool) -> Dict[str, "Flag"]:
    flags = {}

    for e in data.getfind("Flags", raiseerror=False):
        defvalue = e.getbool(".", "default")
        value = e.getbool(".", "value", defvalue)
        name = e.gettext("Name", "")
        truename = e.gettext("True", "")
        falsename = e.gettext("False", "")
        spchars = e.getbool(".", "spchars", False)
        flags[name] = Flag(data if writable else None, e, value, name, truename, falsename,
                           defaultvalue=defvalue, spchars=spchars)

    return flags


def init_steps(data: Union["CWPyElementTree", "CWPyElement"], writable: bool) -> Dict[str, "Step"]:
    steps = {}

    for e in data.getfind("Steps", raiseerror=False):
        defvalue = e.getint(".", "default")
        value = e.getint(".", "value", defvalue)
        name = e.gettext("Name", "")
        valuenames = []
        for ev in e:
            if ev.tag.startswith("Value"):
                valuenames.append(ev.text if ev.text else "")
        spchars = e.getbool(".", "spchars", False)
        steps[name] = Step(data if writable else None, e, value, name, valuenames, defaultvalue=defvalue,
                           spchars=spchars)

    return steps


def init_variants(data: Union["CWPyElementTree", "CWPyElement"], writable: bool) -> Dict[str, "Variant"]:
    variants = {}

    for e in data.getfind("Variants", raiseerror=False):
        defvalue = Variant.value_from_element(e, "defaulttype", "defaultvalue")
        value = Variant.value_from_element(e) if e.get("type", "") != "" else defvalue
        name = e.gettext("Name", "")
        variants[name] = Variant(data if writable else None, e, value, name, defaultvalue=defvalue)

    return variants


class Flag(object):
    def __init__(self, parent: Optional[Union["CWPyElementTree", "CWPyElement"]], data: Optional["CWPyElement"],
                 value: bool, name: str, truename: str, falsename: str, defaultvalue: bool, spchars: bool) -> None:
        self.is_writable = parent is not None and data is not None
        self._parent = parent
        self._data = data
        self.value = value
        self.name = name
        self.truename = truename if truename else ""
        self.falsename = falsename if falsename else ""
        self.defaultvalue = defaultvalue
        self.spchars = spchars
        self.initialization = data.getattr(".", "initialize", "Leave") if data is not None else "Leave"

    def __bool__(self) -> bool:
        return self.value

    def redraw_cards(self, cardspeed: int = -1, overridecardspeed: bool = False) -> None:
        """対応するメニューカードの再描画処理"""
        override_dealspeed = cw.cwpy.override_dealspeed
        force_dealspeed = cw.cwpy.force_dealspeed
        try:
            if cardspeed != -1:
                if overridecardspeed:
                    cw.cwpy.force_dealspeed = cardspeed
                else:
                    cw.cwpy.override_dealspeed = cardspeed
            cw.data.redraw_cards(self.value, flag=self.name)
        finally:
            cw.cwpy.override_dealspeed = override_dealspeed
            cw.cwpy.force_dealspeed = force_dealspeed

    def set(self, value: bool, updatedebugger: bool = True) -> None:
        if self.value != value:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.value = value
            cw.cwpy.update_mcardnames()
            if updatedebugger:
                cw.cwpy.event.refresh_variable(self)

    def reverse(self) -> None:
        self.set(not self.value)

    def get_valuename(self, value: Optional[bool] = None) -> str:
        if value is None:
            value = self.value

        if value:
            s = self.truename
        else:
            s = self.falsename

        if s is None:
            return ""
        else:
            return s

    def write_value(self) -> None:
        if self.is_writable and self.initialization != "EventExit":
            assert self._parent is not None
            assert self._data is not None
            self._data.set("value", str(self.value))
            if isinstance(self._parent, CWPyElementTree):
                self._parent.is_edited = True


def redraw_cards(value: bool, flag: str = "", silent: bool = False) -> None:
    """フラグに対応するメニューカードの再描画処理"""
    quickdeal = cw.cwpy.areaid == cw.AREA_CAMP and cw.cwpy.setting.all_quickdeal
    if cw.cwpy.is_autospread():
        drawflag = False

        for mcard in cw.cwpy.get_mcards(flag=flag):
            mcardflag = mcard.is_flagtrue()

            if mcardflag and mcard.status == "hidden":
                drawflag = True
            elif not mcardflag and not mcard.status == "hidden":
                drawflag = True

        if drawflag:
            cw.cwpy.sdata.moved_mcards = {}  # 再配置情報を破棄
            cw.cwpy.hide_cards(True, flag=flag, quickhide=quickdeal, silent=silent)
            cw.cwpy.deal_cards(flag=flag, quickdeal=quickdeal, silent=silent)

    elif value:
        cw.cwpy.deal_cards(updatelist=False, flag=flag, quickdeal=quickdeal, silent=silent)
    else:
        cw.cwpy.hide_cards(updatelist=False, flag=flag, quickhide=quickdeal, silent=silent)


class Step(object):
    def __init__(self, parent: Optional[Union["CWPyElementTree", "CWPyElement"]], data: Optional["CWPyElement"],
                 value: int, name: str, valuenames: List[str], defaultvalue: int, spchars: bool) -> None:
        self.is_writable = parent is not None and data is not None
        self._parent = parent
        self._data = data
        self.value = value
        self.name = name
        self.valuenames = valuenames
        self.defaultvalue = defaultvalue
        self.spchars = spchars
        self.initialization = data.getattr(".", "initialize", "Leave") if data is not None else "Leave"

    def set(self, value: int, updatedebugger: bool = True) -> None:
        value = cw.util.numwrap(value, 0, len(self.valuenames)-1)
        if self.value != value:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.value = value
            cw.cwpy.update_mcardnames()
            if updatedebugger:
                cw.cwpy.event.refresh_variable(self)

    def up(self) -> None:
        if self.value < len(self.valuenames)-1:
            self.set(self.value + 1)

    def down(self) -> None:
        if not self.value <= 0:
            self.set(self.value - 1)

    def get_valuename(self, value: Optional[int] = None) -> str:
        if value is None:
            value = self.value
        value = cw.util.numwrap(value, 0, len(self.valuenames)-1)

        s = self.valuenames[value]
        if s is None:
            return ""
        else:
            return s

    def write_value(self) -> None:
        if self.is_writable and self.initialization != "EventExit":
            assert self._parent is not None
            assert self._data is not None
            self._data.set("value", str(self.value))
            if isinstance(self._parent, CWPyElementTree):
                self._parent.is_edited = True


class StructVal(object):
    """構造体データ。"""
    def __init__(self, name: str, members: Sequence["VariantValueType"]) -> None:
        self.name = name  # 構造体名
        self.members = members  # メンバ値


# BUG: error: Cannot resolve name "VariantValueType" (possible cyclic definition) (mypy 0.790)
# VariantValueType = Union[str, decimal.Decimal, bool, List["VariantValueType"], StructVal]
VariantValueType = Union[str, decimal.Decimal, bool, List[Union[str, decimal.Decimal, bool]], StructVal]


class Variant(object):
    def __init__(self, parent: Optional[Union["CWPyElementTree", "CWPyElement"]], data: Optional["CWPyElement"],
                 value: VariantValueType, name: str, defaultvalue: VariantValueType) -> None:
        self.is_writable = parent is not None and data is not None
        self._parent = parent
        self._data = data
        self.type = Variant.value_to_type(value)
        self.value = value
        self.name = name
        self.defaultvalue = defaultvalue
        self.initialization = data.getattr(".", "initialize", "Leave") if data is not None else "Leave"

    def set(self, value: VariantValueType, updatedebugger: bool = True) -> None:
        if self.value != value:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.type = Variant.value_to_type(value)
            self.value = value
            cw.cwpy.update_mcardnames()
            if updatedebugger:
                cw.cwpy.event.refresh_variable(self)

    @staticmethod
    def value_to_type(value: VariantValueType) -> str:
        if isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, decimal.Decimal):
            return "Number"
        elif isinstance(value, str):
            return "String"
        elif isinstance(value, StructVal):
            return "Structure"
        else:
            return "List"

    @staticmethod
    def value_from_element(e: "cw.data.CWPyElement", typeattr: str = "type",
                           valueattr: Optional[str] = "value") -> VariantValueType:
        vtype = e.getattr(".", typeattr)
        if vtype == "Boolean":
            if valueattr is None:
                return cw.util.str2bool(e.text)
            else:
                return e.getbool(".", valueattr)
        elif vtype == "Number":
            if valueattr is None:
                return decimal.Decimal(e.text)
            else:
                return decimal.Decimal(e.getattr(".", valueattr))
        elif vtype == "String":
            if valueattr is None:
                return e.text
            else:
                return e.getattr(".", valueattr)
        elif vtype == "Structure":
            name: str = ""
            seq: List[VariantValueType] = []
            check: List[Tuple[str, VariantValueType]] = []
            for ve in e:
                if ve.tag == "StructureName":
                    name = ve.text.lower()
                elif ve.tag == "Member":
                    v = Variant.value_from_element(ve)
                    seq.append(v)
                    check.append((ve.getattr(".", "name").lower(), v))
            if not cw.calculator.is_valid_structure(name, check):
                if not name:
                    name = name if name.upper() else "<No Name>"
                members = [t[0].upper() + "=" + Variant.value_to_str(t[1]) for t in check]
                raise Exception("Invalid structure %s(%s)" % (name, ", ".join(members)))
            info = cw.calculator.struct_info(name)
            for i in range(len(seq), len(info.members)):
                seq.append(info.members[i].defvalue)
            return StructVal(name, seq)
        elif vtype == "List":
            seq = []
            for ve in e:
                if ve.tag == "Value":
                    seq.append(Variant.value_from_element(ve))
            # BUG: error: Cannot resolve name "VariantValueType" (possible cyclic definition) (mypy 0.790)
            # return seq
            return typing.cast(VariantValueType, seq)
        else:
            raise ValueError("Invalid variant type: %s" % vtype)

    @staticmethod
    def value_to_str(value: VariantValueType) -> str:
        def to_str(val: VariantValueType) -> str:
            if isinstance(val, str):
                return "\"" + val.replace("\"", "\"\"") + "\""
            else:
                return Variant.value_to_str(val)

        if isinstance(value, bool):
            return str(value).upper()
        elif isinstance(value, decimal.Decimal):
            s = ("%.8f" % value).rstrip("0").rstrip(".")
            if s == "":
                s = "0"
            return s
        elif isinstance(value, str):
            return value
        elif isinstance(value, StructVal):
            members = cw.calculator.cut_optionalmembers(value.name, value.members)
            return value.name.upper() + "(" + ", ".join(map(to_str, members)) + ")"
        else:
            return "LIST(" + ", ".join(map(to_str, value)) + ")"

    @staticmethod
    def value_to_element(value: VariantValueType, e: "cw.data.CWPyElement", typeattr: str = "type") -> None:
        e.set(typeattr, Variant.value_to_type(value))
        if isinstance(value, StructVal):
            info = cw.calculator.struct_info(value.name)
            e.append(make_element("StructureName", value.name.upper()))
            members = cw.calculator.cut_optionalmembers(info.name, value.members)
            for i, (m, v) in enumerate(zip(info.members[:len(members)], members)):
                e2 = make_element("Member", attrs={"name": m.name.upper()})
                Variant._write_value(e2, v)
                e.append(e2)
        elif isinstance(value, list):
            for val in value:
                ve = make_element("Value")
                Variant.value_to_element(val, ve)
                e.append(ve)
        else:
            e.set("value", Variant.value_to_str(value))

    def string_value(self) -> str:
        return Variant.value_to_str(self.value)

    def write_value(self) -> None:
        if self.is_writable and self.initialization != "EventExit":
            assert self._parent is not None
            assert self._data is not None
            Variant._write_value(self._data, self.value)
            if isinstance(self._parent, CWPyElementTree):
                self._parent.is_edited = True

    @staticmethod
    def _write_value(e: "CWPyElement", val: VariantValueType) -> None:
        # <Value>,<StructureName>,<Member>を削除する
        e_name = e.find("Name")
        del e[:]
        if e_name is not None:
            e.append(e_name)

        Variant.value_to_element(val, e, "type")


# ------------------------------------------------------------------------------
# 宿データ
# ------------------------------------------------------------------------------

class YadoDeletedPathSet(object):
    def __init__(self, yadodir: str, tempdir: str) -> None:
        self.yadodir = yadodir
        self.tempdir = tempdir
        self._s: Set[str] = set()

    def write_list(self) -> None:
        if not os.path.isdir(self.tempdir):
            os.makedirs(self.tempdir)
        fpath = cw.util.join_paths(self.tempdir, "DeletedPaths.temp")
        cw.util.write_textfile(fpath, "\n".join(self), cw.fsync)
        cw.fsync.sync()

    def read_list(self) -> bool:
        fpath = cw.util.join_paths(self.tempdir, "DeletedPaths.temp")
        if os.path.isfile(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                for s in f:
                    s = s.rstrip('\n')
                    if s:
                        self.add(s)
                f.close()
            return True
        else:
            return False

    def __iter__(self) -> Iterator[str]:
        return self._s.__iter__()

    def __contains__(self, path: str) -> bool:
        if path.startswith(self.tempdir):
            path = path.replace(self.tempdir, self.yadodir, 1)

        return path in self._s

    def add(self, path: str, forceyado: bool = False) -> None:
        if path.startswith(self.tempdir):
            path = path.replace(self.tempdir, self.yadodir, 1)

        if not forceyado and cw.cwpy.is_playingscenario():
            cw.cwpy.sdata.deletedpaths.add(path)
        else:
            self._s.add(path)

    def remove(self, path: str) -> None:
        if path.startswith(self.tempdir):
            path = path.replace(self.tempdir, self.yadodir, 1)

        self._s.remove(path)

    def discard(self, path: str) -> None:
        if path in self:
            self.remove(path)

    def update(self, s: Iterable[str]) -> None:
        self._s.update(s)

    def clear(self) -> None:
        self._s.clear()


class YadoData(object):
    name: str
    skindirname: str
    money: int
    imgpaths: List["cw.image.ImageInfo"]
    album: List["cw.header.AdventurerHeader"]
    partys: List["cw.header.PartyHeader"]
    storehouse: List["cw.header.CardHeader"]
    partyrecord: List["cw.header.PartyRecordHeader"]
    recenthistory: "cw.setting.RecentHistory"
    savedjpdcimage: Dict[Tuple[str, str], "cw.header.SavedJPDCImageHeader"]
    saved_variables: Dict[Tuple[str, str],
                          Tuple["cw.data.CWPyElement",
                                Dict[str, bool],
                                Dict[str, int],
                                Dict[str, VariantValueType]]]
    bookmarks: List[Tuple[List[str], str]]

    def __init__(self, yadodir: str, tempdir: str, loadparty: bool = True) -> None:
        cw.fsync.sync()

        # 宿データのあるディレクトリ
        self.yadodir = yadodir
        self.tempdir = tempdir

        # セーブ時に削除する予定のファイルパスの集合
        self.deletedpaths = YadoDeletedPathSet(self.yadodir, self.tempdir)

        # 前回の保存が転送途中で失敗していた場合はリトライする
        self._retry_save()
        cw.util.remove_temp()

        # 冒険の再開ダイアログを開いた時に
        # 選択状態にするパーティのパス
        self.lastparty = ""

        if not os.path.isdir(self.tempdir):
            os.makedirs(self.tempdir)

        # ロード中であればTrue
        self._loading = True

        # セーブが必要な状況であればTrue
        self._changed = False

        # Environment(CWPyElementTree)
        path = cw.util.join_paths(self.yadodir, "Environment.xml")
        self.environment = yadoxml2etree(path)
        e = self.environment.find("Property/Name")
        if e is not None:
            self.name = e.text
        else:
            # データのバージョンが古い場合はProperty/Nameが無い
            self.name = os.path.basename(self.yadodir)
            e = make_element("Name", self.name)
            self.environment.insert("Property", e, 0)
        # 宿の金庫
        self.money = self.environment.getint("Property/Cashbox", 0)

        # スキン
        self.skindirname = self.environment.gettext("Property/Skin", cw.cwpy.setting.skindirname)
        skintype = self.environment.gettext("Property/Type", cw.cwpy.setting.skintype)
        skinpath = cw.util.join_paths("Data/Skin", self.skindirname, "Skin.xml")

        # イメージ
        self.imgpaths = cw.image.get_imageinfos(self.environment.find_exists("Property"))

        # 起動オプション
        optskin = cw.OPTIONS.getstr("force_skin")
        cw.OPTIONS.setstr("force_skin", "")
        if optskin:
            skinpath2 = cw.util.join_paths("Data/Skin", optskin, "Skin.xml")
            if os.path.isfile(skinpath2):
                self.skindirname = optskin
            else:
                s = "スキン「%s」が見つかりません。" % (optskin)
                cw.cwpy.call_modaldlg("ERROR", text=s)
                supported_skin = False

        if not self.skindirname:
            # スキン指定無し
            supported_skin = False
        elif not os.path.isfile(skinpath):
            s = "スキン「%s」が見つかりません。" % (self.skindirname)
            cw.cwpy.call_modaldlg("ERROR", text=s)
            supported_skin = False
        else:
            prop = cw.header.GetProperty(skinpath)
            if prop.attrs.get(None, {}).get("dataVersion", "0") in cw.SUPPORTED_SKIN:
                supported_skin = True
            else:
                skinname = prop.properties.get("Name", self.skindirname)
                s = "「%s」は対応していないバージョンのスキンです。%sをアップデートしてください。" % (skinname, cw.APP_NAME)
                cw.cwpy.call_modaldlg("ERROR", text=s)
                supported_skin = False

        if not supported_skin:
            for name in os.listdir("Data/Skin"):
                path = cw.util.join_paths("Data/Skin", name)
                skinpath = cw.util.join_paths("Data/Skin", name, "Skin.xml")

                if os.path.isdir(path) and os.path.isfile(skinpath):
                    try:
                        prop = cw.header.GetProperty(skinpath)
                        if skintype and prop.properties.get("Type", "") != skintype:
                            continue
                        self.skindirname = name
                        break
                    except Exception:
                        # エラーのあるスキンは無視
                        cw.util.print_ex()
            else:
                self.skindirname = cw.cwpy.setting.skindirname
                skintype = cw.cwpy.setting.skintype

            self.set_skinname(self.skindirname, skintype)

        dataversion = self.environment.getint(".", "dataVersion", 0)
        if dataversion < 1:
            self.update_version()
            self.environment.edit(".", "1", "dataVersion")
            self.environment.write_file()

        self.yadodb = cw.yadodb.YadoDB(self.yadodir)
        self.yadodb.update()

        # パーティリスト(PartyHeader)
        self.partys = self.yadodb.get_parties()
        partypaths = set()
        for party in self.partys:
            dpath = os.path.dirname(party.fpath)
            dpath = cw.util.join_paths(dpath, "Debug")
            fpath = cw.util.join_paths(dpath, "OldTimekeeper.xml")
            if cw.fsync.is_waiting(fpath):
                cw.fsync.sync()
            if os.path.isfile(fpath):
                # タイムキーパーをロールバック
                dst = cw.util.join_paths(dpath, "Timekeeper.xml")
                shutil.move(fpath, dst)

            for fpath in party.get_memberpaths():
                partypaths.add(os.path.normcase(fpath))
        self.sort_parties()

        # 待機中冒険者(AdventurerHeader)
        self.standbys: List[cw.header.AdventurerHeader] = []
        for standby in self.yadodb.get_standbys():
            if os.path.normcase(standby.fpath) not in partypaths:
                self.standbys.append(standby)
        self.sort_standbys()

        # アルバム(AdventurerHeader)
        self.album = self.yadodb.get_album()

        # カード置場(CardHeader)
        self.storehouse = self.yadodb.get_cards()
        self.sort_storehouse()

        # パーティ記録
        self.partyrecord = self.yadodb.get_partyrecord()
        self.sort_partyrecord()

        # 保存済みJPDCイメージ
        self.savedjpdcimage = self.yadodb.get_savedjpdcimage()

        self.yadodb.close()

        # 保存済み状態変数
        self.saved_variables = cw.data.YadoData.get_savedvariables(self.environment)

        # ゲームオーバーに至ったシナリオのデータ
        self.losted_sdata: Optional[cw.data.ScenarioData] = None

        # ブックマーク
        self.bookmarks = []
        for be in self.environment.getfind("Bookmarks", raiseerror=False):
            assert isinstance(be, CWPyElement)
            if be.tag != "Bookmark":
                continue
            bookmark = []
            for e in be.getfind("."):
                bookmark.append(e.text if e.text else "")
            bookmarkpath = be.get("path", "")
            if bookmarkpath == "" and bookmark:
                # 0.12.2以前のバージョンではフルパスが記録されていない場合があるので
                # ここで探して記録する(見つからなかった場合は記録しない)
                bookmarkpath = find_scefullpath(cw.cwpy.setting.get_scedir(), bookmark)
                if bookmarkpath:
                    be.set("path", bookmarkpath)
                    self.environment.is_edited = True

            self.bookmarks.append((bookmark, bookmarkpath))

        # シナリオ履歴
        sctempdir = cw.util.join_paths(cw.tempdir, "Scenario")
        self.recenthistory = cw.setting.RecentHistory(sctempdir, self)

        # 現在選択中のパーティをセット
        optparty = cw.OPTIONS.getstr("party")
        cw.OPTIONS.setstr("party", "")
        loadparty &= self.environment.getbool("Property/NowSelectingParty", "autoload", True)
        self.party: Optional[Party] = None
        if loadparty or optparty:
            pname = self.environment.gettext("Property/NowSelectingParty", "")
            if optparty:
                # 起動オプションでパーティが選択されている
                pdppath = cw.util.join_paths(self.yadodir, "Party")
                pdpath = cw.util.join_paths(pdppath, optparty)
                if os.path.isdir(pdpath):
                    pfile = cw.util.join_paths(pdpath, "Party.xml")
                    if not os.path.isfile(pfile):
                        # 古いデータではParty.xmlでない場合があるのでXMLファイルを探す
                        for fname in os.listdir(pdpath):
                            if cw.util.splitext(fname)[1].lower() == ".xml":
                                pfile = cw.util.join_paths(pdpath, fname)
                                break

                    pname = cw.util.relpath(pfile, self.yadodir)

            if pname:
                path = cw.util.join_paths(self.yadodir, pname)
                seq = [header for header in self.partys if path == header.fpath]

                if seq:
                    self.load_party(seq[0])
                else:
                    cw.OPTIONS.setstr("scenario", "")
                    self.load_party(None)

            else:
                cw.OPTIONS.setstr("scenario", "")
                self.load_party(None)

    def update_version(self) -> None:
        """古いバージョンの宿データであれば更新する。
        """
        cw.fsync.sync()
        nowparty = self.environment.gettext("Property/NowSelectingParty", "")
        ppath = cw.util.join_paths(self.yadodir, "Party")
        for fpath in os.listdir(ppath):
            fpath = cw.util.join_paths(ppath, fpath)
            if os.path.isdir(fpath) or not fpath.lower().endswith(".xml"):
                continue

            # パーティデータが1つのファイルであれば
            # ディレクトリ方式に変換する

            # 変換後のディレクトリ
            dpath = cw.util.splitext(fpath)[0]
            dpath = cw.binary.util.check_duplicate(dpath)
            os.makedirs(dpath)

            if nowparty == cw.util.splitext(os.path.basename(fpath))[0]:
                pname = cw.util.join_paths("Party", os.path.basename(dpath), "Party.xml")
                self.environment.edit("Property/NowSelectingParty", pname)

            # データベース
            carddb = cw.yadodb.YadoDB(dpath, cw.yadodb.PARTY)
            order = 0

            # シナリオログ
            wslpath = cw.util.splitext(fpath)[0] + ".wsl"
            haswsl = os.path.isfile(wslpath)
            if haswsl:
                cw.util.decompress_zip(wslpath, cw.tempdir, "ScenarioLog")

                # 荷物袋内のカード群(ファイルパスのみ)
                files = cw.data.make_element("BackpackFiles")
                party = xml2etree(cw.util.join_paths(cw.tempdir, "ScenarioLog/Party", os.path.basename(fpath)))
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
                    carddata.write_file(path=carddata.fpath)

                    header = cw.header.CardHeader(carddata=e)
                    header.fpath = carddata.fpath
                    carddb.insert_cardheader(header, commit=False, cardorder=order)
                    order += 1

                    path = cw.util.relpath(carddata.fpath, dpath)
                    path = cw.util.join_paths(path)
                    files.append(cw.data.make_element("File", path))

                # 新フォーマットの荷物袋ログ
                path = cw.util.join_paths(cw.tempdir, "ScenarioLog/Backpack.xml")
                etree = CWPyElementTree(element=files)
                etree.write_file(path)

                e_backpack = party.find("Backpack")
                if e_backpack is not None:
                    party.getroot().remove(e_backpack)
                party.write_file()
                shutil.move(party.fpath, cw.util.join_paths(cw.tempdir, "ScenarioLog/Party/Party.xml"))

                wslpath2 = cw.util.join_paths(dpath, "Party.wsl")
                cw.util.compress_zip(cw.util.join_paths(cw.tempdir, "ScenarioLog"), wslpath2, unicodefilename=True)
                cw.util.remove(cw.util.join_paths(cw.tempdir, "ScenarioLog"))

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
                    for e2 in carddata.iter():
                        e2text = cw.util.validate_filepath(e2.text)
                        if e2.tag == "ImagePath" and e2text and not cw.binary.image.path_is_code(e2text):
                            path = cw.util.join_paths(self.yadodir, e2text)
                            if os.path.isfile(path):
                                with open(path, "rb") as f:
                                    imagedata = f.read()
                                    f.close()
                                e2.text = cw.binary.image.data_to_code(imagedata)
                    header.imgpaths = cw.image.get_imageinfos(carddata.find_exists("Property"))

                carddata.write_file(path=carddata.fpath)

                header.fpath = carddata.fpath
                carddb.insert_cardheader(header, commit=False, cardorder=order)
                order += 1

            carddb.commit()
            carddb.close()

            # パーティの基本データを書き込み
            data.remove(".", data.find("Backpack"))
            data.write_file(path=cw.util.join_paths(dpath, "Party.xml"))

            # 旧データを除去
            if haswsl:
                os.remove(wslpath)
            os.remove(fpath)

    def changed(self) -> None:
        """データの変化を通知する。"""
        if not self._loading:
            self._changed = True

    def is_changed(self) -> bool:
        return self._changed

    def is_empty(self) -> bool:
        return not (self.partys or self.standbys or self.storehouse or
                    self.album or self.partyrecord or self.savedjpdcimage or
                    self.get_gossips() or self.get_compstamps() or self.saved_variables)

    def is_loading(self) -> bool:
        """
        ロード中はTrue。
        """
        return self._loading

    def set_skinname(self, skindirname: str, skintype: str) -> None:
        self.skindirname = skindirname
        e = self.environment.find("Property/Skin")
        if e is None:
            prop = self.environment.find_exists("Property")
            prop.append(make_element("Skin", skindirname))
        else:
            e.text = skindirname

        e = self.environment.find("Property/Type")
        if e is None:
            prop = self.environment.find_exists("Property")
            prop.append(make_element("Type", skintype))
        else:
            e.text = skintype

        self.environment.is_edited = True

    def get_showingname(self) -> str:
        return self.name

    def load_party(self, header: Optional["cw.header.PartyHeader"] = None) -> None:
        """
        引数のパーティー名のデータを読み込む。
        パーティー名がNoneの場合はパーティーデータは空になる
        """
        # パーティデータが変更されている場合はxmlをTempに吐き出す
        if self.party:
            self.party.write()
            if self.party.members:
                self.add_party(self.party)

            if self.party.members:
                # 次に冒険の再開ダイアログを開いた時に
                # 選択状態にする
                self.lastparty = self.party.path
            else:
                self.lastparty = ""

        if header:
            self.party = Party(header)
            if self.party.lastscenario or self.party.lastscenariopath:
                cw.cwpy.setting.lastscenario = self.party.lastscenario
                cw.cwpy.setting.lastscenariopath = self.party.lastscenariopath
            if header.fpath.lower().startswith("yado"):
                name = cw.util.relpath(header.fpath, self.yadodir)
            else:
                name = cw.util.relpath(header.fpath, self.tempdir)
            name = cw.util.join_paths(name)
            self.environment.edit("Property/NowSelectingParty", name)

            if header in self.partys:
                self.partys.remove(header)

        else:
            self.party = None
            self.environment.edit("Property/NowSelectingParty", "")

    def add_standbys(self, path: str, sort: bool = True) -> "cw.header.AdventurerHeader":
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        header = self.create_advheader(path)
        header.order = cw.util.new_order(self.standbys)
        self.standbys.append(header)
        if sort:
            self.sort_standbys()
        return header

    def add_album(self, path: str) -> "cw.header.AdventurerHeader":
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        header = self.create_advheader(path, True)
        self.album.append(header)
        cw.util.sort_by_attr(self.album, "name")
        return header

    def add_party(self, party: "Party", sort: bool = True) -> "cw.header.PartyHeader":
        fpath = party.path
        header = self.create_partyheader(fpath)
        header.data = party  # 保存時まで記憶しておく
        self.partys.append(header)
        header.order = cw.util.new_order(self.partys)
        if sort:
            self.sort_parties()
        return header

    def add_partyrecord(self, partyrecord: "cw.thread.StoredParty") -> "cw.header.PartyRecordHeader":
        """パーティ記録を追加する。"""
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        fpath = cw.xmlcreater.create_partyrecord(partyrecord)
        partyrecord.fpath = fpath
        header = cw.header.PartyRecordHeader(partyrecord=partyrecord)
        self.partyrecord.append(header)
        self.sort_partyrecord()
        return header

    def replace_partyrecord(self, partyrecord: "cw.thread.StoredParty") -> "cw.header.PartyRecordHeader":
        """partyrecordと同名のパーティ記録を上書きする。
        同名の情報が無かった場合は、追加する。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        for i, header in enumerate(self.partyrecord):
            if header.name == partyrecord.name:
                return self.set_partyrecord(i, partyrecord)
        return self.add_partyrecord(partyrecord)

    def set_partyrecord(self, index: int, partyrecord: "cw.thread.StoredParty") -> "cw.header.PartyRecordHeader":
        """self.partyrecord[index]をpartyrecordで上書きする。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        header = self.partyrecord[index]
        self.deletedpaths.add(header.fpath)
        fpath = cw.xmlcreater.create_partyrecord(partyrecord)
        partyrecord.fpath = fpath
        header = cw.header.PartyRecordHeader(partyrecord=partyrecord)
        self.partyrecord[index] = header
        return header

    def remove_partyrecord(self, header: "cw.header.PartyRecordHeader") -> None:
        """パーティ記録を削除する。"""
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.partyrecord.remove(header)
        self.deletedpaths.add(header.fpath)

    def remove_emptypartyrecord(self) -> None:
        """メンバが全滅したパーティ記録を削除する。"""
        for header in self.partyrecord[:]:
            for member in header.members:
                if member:
                    break
            else:
                self.partyrecord.remove(header)

    def can_restoreparty(self, partyrecordheader: "cw.header.PartyRecordHeader") -> bool:
        """partyrecordheaderが再結成可能であればTrueを返す。
        """
        for member in partyrecordheader.members:
            if self.can_restore(member):
                return True
        return False

    def can_restore(self, member: str) -> bool:
        """memberがパーティの再結成に応じられるかを返す。
        アクティブでないパーティに所属しているなど、
        応じられない場合はFalseを返す。
        """
        for standby in self.standbys:
            if cw.util.splitext(os.path.basename(standby.fpath))[0] == member:
                return True
        if self.party:
            # 現在のパーティは再結成の前に解散するため
            # standbysの中にいるのと同様に扱う
            for m in self.party.members:
                if cw.util.splitext(os.path.basename(m.fpath))[0] == member:
                    return True
        return False

    def get_restoremembers(self,
                           partyrecordheader: "cw.header.PartyRecordHeader") -> List["cw.header.AdventurerHeader"]:
        """partyrecordheaderの再結成で
        待機メンバでなくなるメンバの一覧を返す。
        """
        seq = []
        for member in partyrecordheader.members:
            for standby in self.standbys:
                if cw.util.splitext(os.path.basename(standby.fpath))[0] == member:
                    seq.append(standby)
                    break
        return seq

    def restore_party(self, partyrecordheader: "cw.header.PartyRecordHeader") -> List["cw.header.AdventurerHeader"]:
        """partyrecordheaderからパーティを再結成する。
        現在操作中のパーティがいた場合は解散される。
        結成されたパーティに属するメンバのheaderのlistを返す。
        所属メンバが宿帳に一人も見つからなかった場合は[]を返す。
        """
        assert cw.cwpy.ydata
        cw.cwpy.ydata.changed()
        if cw.cwpy.ydata.party:
            cw.cwpy.dissolve_party(cleararea=False)
        assert not cw.cwpy.ydata.party
        chgarea = cw.cwpy.areaid not in (2, cw.AREA_BREAKUP)

        members = []
        for member in partyrecordheader.members:
            for standby in self.standbys:
                if cw.util.splitext(os.path.basename(standby.fpath))[0] == member:
                    members.append(standby)
                    break
        if not members:
            # メンバがいない場合は失敗
            return members

        for standby in members:
            self.standbys.remove(standby)

        name = partyrecordheader.name
        money = partyrecordheader.money
        prop = cw.header.GetProperty(partyrecordheader.fpath)
        is_suspendlevelup = cw.util.str2bool(prop.properties["SuspendLevelUp"])
        if self.money < money:
            money = self.money
        self.set_money(-money)
        path = cw.xmlcreater.create_party(members, moneyamount=money, pname=name,
                                          is_suspendlevelup=is_suspendlevelup)
        header = self.create_partyheader(cw.util.join_paths(path, "Party.xml"))

        cw.cwpy.load_party(header, chgarea=chgarea, newparty=True)
        assert cw.cwpy.ydata.party

        # 荷物袋の内容を復元。カード置場にない場合は復元不可。
        # 最初は作者名・シナリオ名・使用回数を使用して検索するが、
        # それで見つからない場合はカード名と解説のみで検索する。
        e = yadoxml2etree(partyrecordheader.fpath, tag="BackpackRecord")
        for ce in e.getfind("."):
            assert isinstance(ce, CWPyElement)
            if ce.tag != "CardRecord":
                continue
            get = False
            name = ce.getattr(".", "name", "")
            desc = ce.getattr(".", "desc", "")
            author = ce.getattr(".", "author", "")
            scenario = ce.getattr(".", "scenario", "")
            uselimit = ce.getint(".", "uselimit", 0)
            for cheader in self.storehouse:
                if cheader.name == name and\
                   cheader.desc == desc and\
                   cheader.author == author and\
                   cheader.scenario == scenario and\
                   cheader.uselimit == uselimit:
                    get = True
                    cw.cwpy.trade(targettype="BACKPACK", header=cheader, sound=False, sort=False)
                    break
            if get:
                continue
            for cheader in self.storehouse:
                if cheader.name == name and\
                   cheader.desc == desc:
                    cw.cwpy.trade(targettype="BACKPACK", header=cheader, sound=False, sort=False)
                    break
        assert self.party
        self.party.backpack.reverse()
        for order, cardheader in enumerate(self.party.backpack):
            cardheader.order = order
        self.party.sort_backpack()

        cw.cwpy.statusbar.change(False)
        cw.cwpy.ydata.party._loading = False
        return members

    def create_advheader(self, path: str = "", album: bool = False,
                         element: Optional["CWPyElement"] = None) -> "cw.header.AdventurerHeader":
        """
        path: xmlのパス。
        album: Trueならアルバム用のAdventurerHeaderを作成。
        element: PropertyタグのElement。
        """
        rootattrs: Dict[str, str] = {}
        if not element:
            element = yadoxml2element(path, "Property", rootattrs=rootattrs)

        return cw.header.AdventurerHeader(element, album, rootattrs=rootattrs)

    def create_cardheader(self, path: str = "", element: Optional["CWPyElement"] = None,
                          owner: Optional["cw.character.Character"] = None) -> "cw.header.CardHeader":
        """
        path: xmlのパス。
        element: PropertyタグのElement。
        """
        if element is None:
            element = yadoxml2element(path, "Property")

        return cw.header.CardHeader(element, owner=owner)

    def create_partyheader(self, path: str = "", element: Optional["CWPyElement"] = None) -> "cw.header.PartyHeader":
        """
        path: xmlのパス。
        element: PropertyタグのElement。
        """
        if element is None:
            element = yadoxml2element(path, "Property")

        return cw.header.PartyHeader(element)

    def create_party(self, header: "cw.header.AdventurerHeader", chgarea: bool = True) -> None:
        """新しくパーティを作る。
        header: AdventurerHeader
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        initmoneyamount = cw.cwpy.setting.initmoneyamount
        if cw.cwpy.setting.initmoneyisinitialcash:
            initmoneyamount = cw.cwpy.setting.initialcash

        if self.money < initmoneyamount:
            money = self.money
        else:
            money = initmoneyamount
        self.set_money(-money)
        path = cw.xmlcreater.create_party([header], moneyamount=money)
        partyheader = self.create_partyheader(cw.util.join_paths(path, "Party.xml"))
        cw.cwpy.load_party(partyheader, chgarea=chgarea)
        cw.cwpy.statusbar.change(False)

    def sort_standbys(self) -> None:
        if cw.cwpy.setting.sort_standbys == "Level":
            cw.util.sort_by_attr(self.standbys, "level", "name", "order")
        elif cw.cwpy.setting.sort_standbys == "Name":
            cw.util.sort_by_attr(self.standbys, "name", "level", "order")
        else:
            cw.util.sort_by_attr(self.standbys, "order")

    def sort_parties(self) -> None:
        if cw.cwpy.setting.sort_parties == "HighestLevel":
            cw.util.sort_by_attr(self.partys, "highest_level", "average_level", "name", "order")
        elif cw.cwpy.setting.sort_parties == "AverageLevel":
            cw.util.sort_by_attr(self.partys, "average_level", "highest_level", "name", "order")
        elif cw.cwpy.setting.sort_parties == "Name":
            cw.util.sort_by_attr(self.partys, "name", "order")
        elif cw.cwpy.setting.sort_parties == "Money":
            cw.util.sort_by_attr(self.partys, "money", "name", "order")
        else:
            cw.util.sort_by_attr(self.partys, "order")

    def sort_storehouse(self, test_aptitude: Optional["cw.character.Character"] = None) -> None:
        if cw.cwpy.setting.sort_cards == "Aptitude" and test_aptitude:
            for card in self.storehouse:
                card.set_testaptitude(test_aptitude)
        sort_cards(self.storehouse, cw.cwpy.setting.sort_cards, cw.cwpy.setting.sort_cardswithstar)
        if cw.cwpy.setting.sort_cards == "Aptitude" and test_aptitude:
            for card in self.storehouse:
                card.set_testaptitude(None)

    def sort_partyrecord(self) -> None:
        cw.util.sort_by_attr(self.partyrecord, "name")

    def save(self) -> None:
        """宿データをセーブする。"""
        if isinstance(cw.cwpy.sdata, cw.data.SystemData):
            cw.cwpy.sdata.save_variables()
        # カード置場の順序を記憶しておく
        cardorder: Dict[str, int] = {}
        cardtable: Dict[str, cw.header.CardHeader] = {}
        for header in self.storehouse:
            if header.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(header.fpath, self.yadodir)
            else:
                fpath = cw.util.relpath(header.fpath, self.tempdir)
                header.fpath = header.fpath.replace(self.tempdir, self.yadodir, 1)
            fpath = cw.util.join_paths(fpath)
            cardorder[fpath] = header.order
            cardtable[fpath] = header
        # 宿帳の順序を記憶しておく
        adventurerorder = {}
        adventurertable = {}
        for advheader in self.standbys:
            if advheader.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(advheader.fpath, self.yadodir)
            else:
                fpath = cw.util.relpath(advheader.fpath, self.tempdir)
                advheader.fpath = advheader.fpath.replace(self.tempdir, self.yadodir, 1)
            fpath = cw.util.join_paths(fpath)
            adventurerorder[fpath] = advheader.order
            adventurertable[fpath] = advheader

        # アルバム(順序情報なし)
        for advheader in self.album:
            if not advheader.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(advheader.fpath, self.tempdir)
                advheader.fpath = advheader.fpath.replace(self.tempdir, self.yadodir, 1)

        # ScenarioLog更新
        if cw.cwpy.is_playingscenario():
            assert isinstance(cw.cwpy.sdata, ScenarioData)
            logfilepath = cw.cwpy.advlog.logfilepath
            cw.cwpy.sdata.update_log()
            cw.cwpy.advlog.resume_scenario(logfilepath)

        # environment.xml書き出し
        self.environment.write_xml()

        # party.xmlと冒険者のxmlファイル書き出し
        if self.party:
            self.party.write()

        self.deletedpaths.write_list()

        cw.fsync.sync()
        self._transfer_temp()

        def commit_timekeeper(ppath: str, is_adventuring: bool) -> None:
            # タイムキーパーをコミット
            dpath = os.path.dirname(ppath)
            if not dpath.lower().startswith("yado"):
                dpath = dpath.replace(cw.cwpy.tempdir, cw.cwpy.yadodir, 1)
            dpath = cw.util.join_paths(dpath, "Debug")
            fpath = cw.util.join_paths(dpath, "OldTimekeeper.xml")
            if cw.fsync.is_waiting(fpath):
                cw.fsync.sync()
            if os.path.isfile(fpath):
                cw.util.remove(fpath)
            if not is_adventuring or not cw.cwpy.setting.enabled_timekeeper:
                fpath = cw.util.join_paths(dpath, "Timekeeper.xml")
                if cw.fsync.is_waiting(fpath):
                    cw.fsync.sync()
                if os.path.isfile(fpath):
                    cw.util.remove(fpath)
            cw.util.remove_emptydir(dpath)

        # 各パーティの荷物袋のデータを保存する
        def update_backpack(party: Party) -> None:
            # カード置場の順序を記憶しておく
            cardorder = {}
            ppath = os.path.dirname(party.path)
            yadodir = party.get_yadodir()
            tempdir = party.get_tempdir()
            cardtable = {}
            for header in party.backpack:
                header.do_write()
                if header.fpath.lower().startswith("yado"):
                    fpath = cw.util.relpath(header.fpath, yadodir)
                else:
                    fpath = cw.util.relpath(header.fpath, tempdir)
                    header.fpath = header.fpath.replace(self.tempdir, self.yadodir, 1)
                fpath = cw.util.join_paths(fpath)
                cardorder[fpath] = header.order
                cardtable[fpath] = header
            carddb = cw.yadodb.YadoDB(ppath, mode=cw.yadodb.PARTY)
            carddb.update(cards=cardtable, cardorder=cardorder)
            carddb.close()
        if self.party:
            commit_timekeeper(self.party.path, cw.cwpy.is_playingscenario())
            update_backpack(self.party)
        partyorder: Dict[str, int] = {}
        for party in self.partys:
            commit_timekeeper(party.fpath, party.is_adventuring())
            if party.data:
                update_backpack(party.data)
                if party.fpath.lower().startswith(self.tempdir.lower()):
                    party.fpath = party.fpath.replace(self.tempdir, self.yadodir, 1)
                party.data = None
            partyorder[cw.util.relpath(party.fpath, self.yadodir)] = party.order

        partyrecord = {}
        for partyrecordheader in self.partyrecord:
            if partyrecordheader.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(partyrecordheader.fpath, self.yadodir)
            else:
                fpath = cw.util.relpath(partyrecordheader.fpath, self.tempdir)
                partyrecordheader.fpath = partyrecordheader.fpath.replace(self.tempdir, self.yadodir, 1)
            partyrecord[fpath] = partyrecordheader

        savedjpdcimage = {}
        for savedjpdcimageheader in self.savedjpdcimage.values():
            if savedjpdcimageheader.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(savedjpdcimageheader.fpath, self.yadodir)
            else:
                fpath = cw.util.relpath(savedjpdcimageheader.fpath, self.tempdir)
                savedjpdcimageheader.fpath = savedjpdcimageheader.fpath.replace(self.tempdir, self.yadodir, 1)
            savedjpdcimage[fpath] = savedjpdcimageheader

        # カードデータベースを更新
        @synclock(_lock)
        def update_database(yadodir: str) -> None:
            cw.fsync.sync()
            yadodb = cw.yadodb.YadoDB(yadodir)
            yadodb.update(cards=cardtable,
                          adventurers=adventurertable,
                          cardorder=cardorder,
                          adventurerorder=adventurerorder,
                          partyorder=partyorder,
                          partyrecord=partyrecord,
                          savedjpdcimage=savedjpdcimage)
            yadodb.close()
        thr = threading.Thread(target=update_database, kwargs={"yadodir": self.yadodir})
        thr.start()

        cw.cwpy.clear_selection()
        self._changed = False

    def _retry_save(self) -> None:
        """TempからYadoへの転送中に失敗した保存処理を再実行する。
        """
        if self.deletedpaths.read_list():
            self._transfer_temp()

    def _transfer_temp(self) -> None:
        # TEMPのファイルを移動
        cw.fsync.sync()
        deltempfpath = cw.util.join_paths(self.deletedpaths.tempdir, "DeletedPaths.temp")
        for dpath, _dnames, fnames in os.walk(self.tempdir):
            for fname in fnames:
                path = cw.util.join_paths(dpath, fname)
                if path == deltempfpath:
                    continue
                if os.path.isfile(path):
                    dstpath = path.replace(self.tempdir, self.yadodir, 1)
                    cw.util.rename_file(path, dstpath)

        # 削除予定のファイル削除
        # Materialディレクトリにある空のフォルダも削除
        materialdir = cw.util.join_paths(self.yadodir, "Material")

        # 安全のためこれらのパスは削除の際に無視する
        ignores = set()
        for ipath in (cw.cwpy.yadodir, cw.cwpy.tempdir,
                      os.path.join(cw.cwpy.yadodir, "Adventurer"),
                      os.path.join(cw.cwpy.yadodir, "Party"),
                      os.path.join(cw.cwpy.yadodir, "Album"),
                      os.path.join(cw.cwpy.yadodir, "CastCard"),
                      os.path.join(cw.cwpy.yadodir, "SkillCard"),
                      os.path.join(cw.cwpy.yadodir, "ItemCard"),
                      os.path.join(cw.cwpy.yadodir, "BeastCard"),
                      os.path.join(cw.cwpy.yadodir, "InfoCard"),
                      os.path.join(cw.cwpy.yadodir, "Material")):
            ignores.add(os.path.normpath(os.path.normcase(ipath)))

        # 削除実行
        delfailurepaths: Set[str] = set()
        for path in self.deletedpaths:
            if os.path.normpath(os.path.normcase(path)) in ignores:
                continue
            cw.util.remove(path)
            dpath = os.path.dirname(path)
            if dpath.startswith(materialdir) and os.path.isdir(dpath) and not os.listdir(dpath):
                cw.util.remove(dpath)

        self.deletedpaths.clear()
        # 宿のtempフォルダを空にする
        cw.util.remove(deltempfpath)
        cw.util.remove(self.tempdir)

        # BUG: 環境によってファイルやフォルダの削除が失敗する事がある
        #      (WindowsError: [Error 5] アクセスが拒否されました)。
        #      そうしたファイルは削除リストに残しておき、後で削除する。
        for path in delfailurepaths:
            self.deletedpaths.add(path)

    # --------------------------------------------------------------------------
    # ゴシップ・シナリオ終了印用メソッド
    # --------------------------------------------------------------------------

    def get_gossips(self) -> Set[str]:
        """ゴシップ名をset型で返す。"""
        return set([e.text for e in self.environment.getfind("Gossips") if e.text])

    def get_compstamps(self) -> Set[str]:
        """冒険済みシナリオ名をset型で返す。"""
        return set([e.text for e in self.environment.getfind("CompleteStamps") if e.text])

    def get_gossiplist(self) -> List[str]:
        """ゴシップ名をlist型で返す。"""
        return [e.text for e in self.environment.getfind("Gossips") if e.text]

    def get_compstamplist(self) -> List[str]:
        """冒険済みシナリオ名をlist型で返す。"""
        return [e.text for e in self.environment.getfind("CompleteStamps") if e.text]

    def has_compstamp(self, name: str) -> bool:
        """冒険済みシナリオかどうかbool値で返す。
        name: シナリオ名。
        """
        for e in self.environment.getfind("CompleteStamps"):
            if e.text and e.text == name:
                return True

        return False

    def has_gossip(self, name: str) -> bool:
        """ゴシップを所持しているかどうかbool値で返す。
        name: ゴシップ名
        """
        for e in self.environment.getfind("Gossips"):
            if e.text and e.text == name:
                return True

        return False

    def set_compstamp(self, name: str) -> None:
        """冒険済みシナリオ印をセットする。シナリオプレイ中に取得した
        シナリオ印はScenarioDataのリストに登録する。
        name: シナリオ名
        """
        if not self.has_compstamp(name):
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            e = make_element("CompleteStamp", name)
            self.environment.append("CompleteStamps", e)

            if cw.cwpy.is_playingscenario():
                if cw.cwpy.sdata.compstamps.get(name) is False:
                    cw.cwpy.sdata.compstamps.pop(name)
                else:
                    cw.cwpy.sdata.compstamps[name] = True

    def set_gossip(self, name: str) -> None:
        """ゴシップをセットする。シナリオプレイ中に取得した
        ゴシップはScenarioDataのリストに登録する。
        name: ゴシップ名
        """
        if not self.has_gossip(name):
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            e = make_element("Gossip", name)
            self.environment.append("Gossips", e)

            if cw.cwpy.is_playingscenario():
                if cw.cwpy.sdata.gossips.get(name) is False:
                    cw.cwpy.sdata.gossips.pop(name)
                else:
                    cw.cwpy.sdata.gossips[name] = True

    def remove_compstamp(self, name: str) -> None:
        """冒険済みシナリオ印を削除する。シナリオプレイ中に削除した
        シナリオ印はScenarioDataのリストから解除する。
        name: シナリオ名
        """
        elements = [e for e in self.environment.getfind("CompleteStamps") if e.text == name]

        for e in elements:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.environment.remove("CompleteStamps", e)

        if elements and cw.cwpy.is_playingscenario():
            if cw.cwpy.sdata.compstamps.get(name) is True:
                cw.cwpy.sdata.compstamps.pop(name)
            else:
                cw.cwpy.sdata.compstamps[name] = False

    def remove_gossip(self, name: str) -> None:
        """ゴシップを削除する。シナリオプレイ中に削除した
        ゴシップはScenarioDataのリストから解除する。
        name: ゴシップ名
        """
        elements = [e for e in self.environment.getfind("Gossips") if e.text == name]

        for e in elements:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.environment.remove("Gossips", e)

        if elements and cw.cwpy.is_playingscenario():
            if cw.cwpy.sdata.gossips.get(name) is True:
                cw.cwpy.sdata.gossips.pop(name)
            else:
                cw.cwpy.sdata.gossips[name] = False

    def clear_compstamps(self) -> None:
        """冒険済みシナリオ印を全て削除する。"""

        for e in list(self.environment.getfind("CompleteStamps")):
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.environment.remove("CompleteStamps", e)

            if cw.cwpy.is_playingscenario():
                name = e.text
                if cw.cwpy.sdata.compstamps.get(name) is True:
                    cw.cwpy.sdata.compstamps.pop(name)
                else:
                    cw.cwpy.sdata.compstamps[name] = False
        assert len(self.environment.getfind("CompleteStamps")) == 0

    def clear_gossips(self) -> None:
        """ゴシップを全て削除する。"""

        for e in list(self.environment.getfind("Gossips")):
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.environment.remove("Gossips", e)

            if cw.cwpy.is_playingscenario():
                name = e.text
                if cw.cwpy.sdata.gossips.get(name) is True:
                    cw.cwpy.sdata.gossips.pop(name)
                else:
                    cw.cwpy.sdata.gossips[name] = False
        assert len(self.environment.getfind("Gossips")) == 0

    def find_gossip(self, matcher: Callable[[str], bool], startindex: int) -> int:
        """
        matcher(name)がTrueになるゴシップを
        startindexの位置から検索し、見つかった位置を返す。
        """
        e_gossips = self.environment.find("Gossips")
        if e_gossips is not None:
            for i, e_gossip in enumerate(e_gossips[startindex:]):
                if matcher(e_gossip.text):
                    return i + startindex
        return -1

    def get_gossip_at(self, index: int) -> str:
        """指定位置のゴシップ名を返す。"""
        e_gossips = self.environment.find("Gossips")
        if e_gossips is None:
            raise Exception("No gossips.")
        e = e_gossips[index]
        return e.text

    def gossips_len(self) -> int:
        """ゴシップ数を返す。"""
        e_gossips = self.environment.find("Gossips")
        if e_gossips is None:
            return 0
        else:
            return len(e_gossips)

    def set_money(self, value: int, blink: bool = False) -> None:
        """金庫に入っている金額を変更する。
        現在の所持金にvalue値をプラスするので注意。
        """
        if value != 0:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.money += value
            self.money = cw.util.numwrap(self.money, 0, 9999999)
            self.environment.edit("Property/Cashbox", str(self.money))
            showbuttons = not cw.cwpy.is_playingscenario() or not cw.cwpy.is_runningevent()
            cw.cwpy.statusbar.change(showbuttons)
            cw.cwpy.has_inputevent = True
            if blink:
                if cw.cwpy.statusbar.yadomoney:
                    cw.animation.start_animation(cw.cwpy.statusbar.yadomoney, "blink")

    # --------------------------------------------------------------------------
    # パーティ連れ込み
    # --------------------------------------------------------------------------

    def join_npcs(self) -> None:
        """
        シナリオのNPCを宿に連れ込む。
        """
        r_gene = re.compile("＠Ｇ\\d{10}$")
        for fcard in cw.cwpy.get_fcards():
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            fcard.set_fullrecovery()

            # 必須クーポンを所持していなかったら補填
            if not fcard.has_age() or not fcard.has_sex():
                cw.cwpy.play_sound("signal")
                cw.cwpy.call_modaldlg("DATACOMP", ccard=fcard)

            # システムクーポン
            fcard.set_coupon("＿" + fcard.name, int(fcard.level * (fcard.level-1) * fcard.get_levelcoeff()))
            fcard.set_coupon("＠レベル原点", fcard.level)
            if not fcard.has_coupon("＠ＥＰ"):
                fcard.set_coupon("＠ＥＰ", 0)
            talent = fcard.get_talent()

            value = 10
            for nature in cw.cwpy.setting.natures:
                if "＿" + nature.name == talent:
                    value = nature.levelmax
                    break

            fcard.set_coupon("＠本来の上限", max(value, fcard.level))
            if not fcard.has_coupon("＠レベル上限"):
                fcard.set_coupon("＠レベル上限", max(value, fcard.level))

            for coupon in fcard.get_coupons():
                if r_gene.match(coupon):
                    break
            else:
                gene = cw.header.Gene()
                gene.set_talentbit(talent)
                fcard.set_coupon("＠Ｇ" + gene.get_str(), 0)

            data = fcard.data

            # 所持カードの素材ファイルコピー
            for cardtype in ("SkillCard", "ItemCard", "BeastCard"):
                for e in data.getfind("%ss" % (cardtype)):
                    # 対象カード名取得
                    name = e.gettext("Property/Name", "noname")
                    name = cw.util.repl_dischar(name)
                    # 素材ファイルコピー
                    dstdir = cw.util.join_paths(self.yadodir,
                                                "Material", cardtype, name if name else"noname")
                    dstdir = cw.util.dupcheck_plus(dstdir)
                    can_loaded_scaledimage = e.getbool(".", "scaledimage", False)
                    cw.cwpy.copy_materials(e, dstdir, can_loaded_scaledimage=can_loaded_scaledimage)

            # カード画像コピー
            name = cw.util.repl_dischar(fcard.name) if fcard.name else "noname"
            e = data.find_exists("Property")
            dstdir = cw.util.join_paths(self.yadodir, "Material", "Adventurer", name)
            dstdir = cw.util.dupcheck_plus(dstdir)
            can_loaded_scaledimage = data.getbool(".", "scaledimage", False)
            cw.cwpy.copy_materials(e, dstdir, can_loaded_scaledimage=can_loaded_scaledimage)
            # xmlファイル書き込み
            data.getroot().tag = "Adventurer"
            path = cw.util.join_paths(self.tempdir, "Adventurer", name + ".xml")
            path = cw.util.dupcheck_plus(path)
            data.write_file(path)
            # 待機中冒険者のリストに追加
            self.add_standbys(path, sort=False)
        self.sort_standbys()

    # --------------------------------------------------------------------------
    # ここからpathリスト取得用メソッド
    # --------------------------------------------------------------------------

    def get_nowplayingpaths(self) -> Set[str]:
        """wslファイルを読み込んで、
        現在プレイ中のシナリオパスの集合を返す。
        """
        cw.fsync.sync()
        seq = []

        for dpath in (self.yadodir, self.tempdir):
            dpath = cw.util.join_paths(dpath, "Party")
            if not os.path.isdir(dpath):
                continue

            for dname in os.listdir(dpath):
                dpath2 = cw.util.join_paths(dpath, dname)
                if not os.path.isdir(dpath2):
                    continue

                for name in os.listdir(dpath2):
                    path = cw.util.join_paths(dpath2, name)
                    if name.endswith(".wsl") and os.path.isfile(path)\
                            and path not in self.deletedpaths:
                        e = cw.util.get_elementfromzip(path, "ScenarioLog.xml", "Property")
                        path = e.gettext("WsnPath")
                        path = cw.util.get_linktarget(path)
                        path = cw.util.get_keypath(path)
                        seq.append(path)

        return set(seq)

    def get_partypaths(self) -> List[str]:
        """パーティーのxmlファイルのpathリストを返す。"""
        cw.fsync.sync()
        seq = []
        dpath = cw.util.join_paths(self.yadodir, "Party")

        for fname in os.listdir(dpath):
            fpath = cw.util.join_paths(dpath, fname)

            if os.path.isfile(fpath) and fname.endswith(".xml"):
                seq.append(fpath)

        return seq

    def get_storehousepaths(self) -> List[str]:
        """BeastCard, ItemCard, SkillCardのディレクトリにあるカードの
        xmlのpathリストを返す。
        """
        cw.fsync.sync()
        seq = []

        for dname in ("BeastCard", "ItemCard", "SkillCard"):
            for fname in os.listdir(cw.util.join_paths(self.yadodir, dname)):
                fpath = cw.util.join_paths(self.yadodir, dname, fname)

                if os.path.isfile(fpath) and fname.endswith(".xml"):
                    seq.append(fpath)

        return seq

    def get_standbypaths(self) -> List[str]:
        """パーティーに所属していない待機中冒険者のxmlのpathリストを返す。"""
        cw.fsync.sync()
        seq = []

        for header in self.partys:
            paths = header.get_memberpaths()
            seq.extend(paths)

        members = set(seq)
        seq = []

        for fname in os.listdir(cw.util.join_paths(self.yadodir, "Adventurer")):
            fpath = cw.util.join_paths(self.yadodir, "Adventurer", fname)

            if os.path.isfile(fpath) and fname.endswith(".xml"):
                if fpath not in members:
                    seq.append(fpath)

        return seq

    def get_albumpaths(self) -> List[str]:
        """アルバムにある冒険者のxmlのpathリストを返す。"""
        cw.fsync.sync()
        seq = []

        for fname in os.listdir(cw.util.join_paths(self.yadodir, "Album")):
            fpath = cw.util.join_paths(self.yadodir, "Album", fname)

            if os.path.isfile(fpath) and fname.endswith(".xml"):
                seq.append(fpath)

        return seq

    # --------------------------------------------------------------------------
    # ブックマーク
    # --------------------------------------------------------------------------

    def add_bookmark(self, spaths: List[str], path: str) -> None:
        """シナリオのブックマークを追加する。"""
        self.changed()
        self.bookmarks.append((spaths, path))
        be = self.environment.find("Bookmarks")
        if be is None:
            be = make_element("Bookmarks")
            self.environment.append(".", be)
        e = make_element("Bookmark")
        for p in spaths:
            e2 = make_element("Path", p)
            e.append(e2)
        e.set("path", path)
        self.environment.is_edited = True
        be.append(e)

    def set_bookmarks(self, bookmarks: List[Tuple[List[str], str]]) -> None:
        """シナリオのブックマーク群を入れ替える。"""
        self.changed()
        self.bookmarks = bookmarks

        be = self.environment.find("Bookmarks")
        if be is None:
            be = make_element("Bookmarks")
            self.environment.append(".", be)
        else:
            be.clear()

        for spaths, path in bookmarks:
            e = make_element("Bookmark")
            for p in spaths:
                e2 = make_element("Path", p)
                e.append(e2)
            e.set("path", path)
            be.append(e)
        self.environment.is_edited = True

    @staticmethod
    def get_savedvariables(environment: "cw.data.CWPyElementTree") \
            -> Dict[Tuple[str, str],
                    Tuple["cw.data.CWPyElement",
                          Dict[str, bool],
                          Dict[str, int],
                          Dict[str, VariantValueType]]]:
        """保存された状態変数を((scenario, author), (element, flags, steps, variants))で返す。"""
        data = environment.find("SavedVariables")
        if data is None:
            return {}
        return YadoData.get_savedvariables_with_scenario(data)

    _VarsKey = TypeVar("_VarsKey", Tuple[str, str], str)

    @staticmethod
    def _get_vartables(e: "cw.data.CWPyElement") -> Tuple[Dict[str, bool],
                                                          Dict[str, int],
                                                          Dict[str, VariantValueType]]:
        assert e.tag == "Variables"
        flags = {}
        for e_flag in e.getfind("Flags", raiseerror=False):
            assert isinstance(e_flag, cw.data.CWPyElement)
            name = e_flag.getattr(".", "name", "")
            if not name:
                continue
            flags[name] = e_flag.getbool(".", "value", False)
        steps = {}
        for e_step in e.getfind("Steps", raiseerror=False):
            assert isinstance(e_step, cw.data.CWPyElement)
            name = e_step.getattr(".", "name", "")
            if not name:
                continue
            steps[name] = e_step.getint(".", "value", 0)
        variants = {}
        for e_variant in e.getfind("Variants", raiseerror=False):
            assert isinstance(e_variant, cw.data.CWPyElement)
            name = e_variant.getattr(".", "name", "")
            if not name:
                continue
            value = Variant.value_from_element(e_variant)
            variants[name] = value
        return flags, steps, variants

    @staticmethod
    def get_savedvariables_with_skin(data: "cw.data.CWPyElement") \
            -> Dict[str,
                    Tuple["cw.data.CWPyElement",
                          Dict[str, bool],
                          Dict[str, int],
                          Dict[str, VariantValueType]]]:
        d = {}
        for e in data:
            assert isinstance(e, cw.data.CWPyElement)
            if e.tag != "Variables":
                continue
            key = e.getattr(".", "key", "")
            flags, steps, variants = cw.data.YadoData._get_vartables(e)
            d[key] = (e, flags, steps, variants)
        return d

    @staticmethod
    def get_savedvariables_with_scenario(data: "cw.data.CWPyElement") \
            -> Dict[Tuple[str, str],
                    Tuple["cw.data.CWPyElement",
                          Dict[str, bool],
                          Dict[str, int],
                          Dict[str, VariantValueType]]]:
        d = {}
        for e in data:
            assert isinstance(e, cw.data.CWPyElement)
            if e.tag != "Variables":
                continue
            scenario = e.getattr(".", "scenario", "")
            author = e.getattr(".", "author", "")
            if not scenario and not author:
                continue
            key = (scenario, author)
            flags, steps, variants = cw.data.YadoData._get_vartables(e)
            d[key] = (e, flags, steps, variants)
        return d

    def save_variables(self, scenario: str, author: str, complete: bool, flags: Dict[str, Flag], steps: Dict[str, Step],
                       variants: Dict[str, Variant], debuglog: Optional["cw.debug.logging.DebugLog"]) -> None:
        target = ("None",) if complete else ("Complete", "None")
        d_flags = {}
        for flag in flags.values():
            if flag.initialization in target:
                d_flags[flag.name] = flag.value
                if debuglog:
                    debuglog.add_flag(flag.name)
        d_steps = {}
        for step in steps.values():
            if step.initialization in target:
                d_steps[step.name] = step.value
                if debuglog:
                    debuglog.add_step(step.name)
        d_variants = {}
        for variant in variants.values():
            if variant.initialization in target:
                d_variants[variant.name] = variant.value
                if debuglog:
                    debuglog.add_variant(variant.name)
        key = (scenario, author)

        if key in self.saved_variables:
            data = self.environment.find_exists("SavedVariables")
            e, _, _, _ = self.saved_variables[key]
            if not d_flags and not d_steps and not d_variants:
                data.remove(e)
                if debuglog:
                    debuglog.remove_variables()
                self.environment.is_edited = True
                return
            e.clear()
        else:
            if not d_flags and not d_steps and not d_variants:
                return
            v_data = self.environment.find("SavedVariables")
            if v_data is None:
                v_data = make_element("SavedVariables")
                self.environment.append(".", v_data)
            data = v_data
            e = make_element("Variables")
            data.append(e)
        e.set("scenario", scenario)
        e.set("author", author)
        if d_flags:
            e_flags = make_element("Flags")
            e.append(e_flags)
            for name, b_value in d_flags.items():
                e_flags.append(make_element("Flag", attrs={"name": name,
                                                           "value": str(b_value)}))
        if d_steps:
            e_steps = make_element("Steps")
            e.append(e_steps)
            for name, i_value in d_steps.items():
                e_steps.append(make_element("Step", attrs={"name": name,
                                                           "value": str(i_value)}))
        if d_variants:
            e_variants = make_element("Variants")
            e.append(e_variants)
            for name, v_value in d_variants.items():
                ve = make_element("Variant", attrs={"name": name})
                Variant.value_to_element(v_value, ve)
                e_variants.append(ve)

        self.environment.is_edited = True
        self.saved_variables[key] = (e, d_flags, d_steps, d_variants)

    def remove_savedvariables(self, scenario: str, author: str) -> None:
        key = (scenario, author)
        d = self.saved_variables.get(key, None)
        if not d:
            return
        e, _, _, _ = d
        data = self.environment.find_exists("SavedVariables")
        data.remove(e)
        del self.saved_variables[key]


def find_scefullpath(scepath: str, spaths: List[str]) -> str:
    """開始ディレクトリscepathから経路spathsを
    辿った結果得られたフルパスを返す。
    辿れなかった場合は""を返す。
    """
    bookmarkpath = ""
    for p in spaths:
        scepath = cw.util.get_linktarget(scepath)
        scepath = cw.util.join_paths(scepath, p)
        if not os.path.exists(scepath):
            break
    else:
        bookmarkpath = os.path.abspath(scepath)
        bookmarkpath = os.path.normpath(scepath)
    return bookmarkpath


class Party(object):
    name: str
    money: int

    members: List["cw.data.CWPyElementTree"]
    backpack: List["cw.header.CardHeader"]

    is_suspendlevelup: bool
    sorted_backpack_by_order: bool

    def __init__(self, header: "cw.header.PartyHeader", partyinfoonly: bool = True) -> None:
        self._init(header, partyinfoonly)

    def _init(self, header: "cw.header.PartyHeader", partyinfoonly: bool = True) -> None:
        path = header.fpath

        # True時は、エリア移動中にPlayerCardスプライトを新規作成する
        self._loading = True

        self.members = []
        if not header.data:
            self.backpack: List[cw.header.CardHeader] = []
            self.backpack_moved: List[cw.header.CardHeader] = []
        self.path = path

        # キャンセル可能な対象消去メンバ(互換機能)
        self.vanished_pcards: List[cw.sprite.card.PlayerCard] = []

        # パーティデータ(CWPyElementTree)
        self.data = yadoxml2etree(path)
        # パーティ名
        self.name = self.data.gettext("Property/Name", "")
        # パーティ所持金
        self.money = self.data.getint("Property/Money", 0)

        # 現在プレイ中のシナリオ
        self.lastscenario = []
        self.lastscenariopath = self.data.getattr("Property/LastScenario", "path", "")
        for e in self.data.getfind("Property/LastScenario", raiseerror=False):
            self.lastscenario.append(e.text)

        # レベルアップ停止中か
        self.is_suspendlevelup = self.data.getbool("Property/SuspendLevelUp", False)

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
                for cardheader in carddb.get_cards():
                    if cardheader.moved == 0:
                        self.backpack.append(cardheader)
                    else:
                        self.backpack_moved.append(cardheader)
                carddb.close()
            self.sort_backpack()
            self.sorted_backpack_by_order = False

    def get_showingname(self) -> str:
        return self.name

    def sort_backpack(self, sorttype: Optional[str] = None,
                      test_aptitude: Optional["cw.character.Character"] = None) -> None:
        if sorttype is None:
            sorttype = cw.cwpy.setting.sort_cards
        if sorttype == "Aptitude" and test_aptitude:
            for card in self.backpack:
                card.set_testaptitude(test_aptitude)
        sort_cards(self.backpack, sorttype, cw.cwpy.setting.sort_cardswithstar)
        if sorttype == "Aptitude" and test_aptitude:
            for card in self.backpack:
                card.set_testaptitude(None)
        self.sorted_backpack_by_order = (sorttype == "order")

    def find_keycode(self, keycode: str, skill: bool = True, item: bool = True, beast: bool = True,
                     hand: bool = True, condition: str = "Has") -> Optional["cw.header.CardHeader"]:
        """指定されたキーコードを所持しているか。
        当該キーコードを含むカードを返す。
        見つからなかった場合はNoneを返す。
        conditionが"HasNot"の場合はキーコードを含まないカードを返す。
        """
        if not self.sorted_backpack_by_order:
            self.sort_backpack(sorttype="order")

        for header in self.backpack:
            if not skill and header.type == "SkillCard":
                continue
            elif not item and header.type == "ItemCard":
                continue
            elif not beast and header.type == "BeastCard":
                continue

            if condition == "HasNot":
                match = keycode not in header.get_keycodes()
            else:
                match = keycode in header.get_keycodes()
            if match:
                return header

        return None

    def get_relpath(self) -> str:
        ppath = os.path.dirname(self.path)
        if ppath.lower().startswith("yado"):
            relpath = cw.util.relpath(ppath, cw.cwpy.yadodir)
        else:
            relpath = cw.util.relpath(ppath, cw.cwpy.tempdir)
        return cw.util.join_paths(relpath)

    def get_yadodir(self) -> str:
        return cw.util.join_paths(cw.cwpy.yadodir, self.get_relpath())

    def get_tempdir(self) -> str:
        return cw.util.join_paths(cw.cwpy.tempdir, self.get_relpath())

    def is_loading(self) -> bool:
        """membersのデータを元にPlayerCardインスタンスを
        生成していなかったら、Trueを返す。
        """
        return self._loading

    def reload(self) -> None:
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        header = cw.header.PartyHeader(data=self.data.find_exists("Property"))
        header.data = self
        self._init(header)

    def add(self, header: "cw.header.AdventurerHeader", data: Optional["CWPyElementTree"] = None) -> None:
        """
        メンバーを追加する。
        """
        pcardsnum = len(self.members)

        # パーティ人数が6人だったら処理中断
        if pcardsnum >= 6:
            return

        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        s = os.path.basename(header.fpath)
        s = cw.util.splitext(s)[0]
        e = self.data.make_element("Member", s)
        if not data:
            data = yadoxml2etree(header.fpath)
        pcards = cw.cwpy.get_pcards()
        if pcards:
            # 欠けているindexがあったら隙間に挿入する
            for i, pcard in enumerate(pcards):
                if i != pcard.index:
                    index = i
                    break
            else:
                index = pcards[-1].index + 1
        else:
            index = 0
        self.members.insert(index, data)
        self.data.insert("Property/Members", e, index)
        pos_noscale = (9 + 95 * index + 9 * index, 285)
        pcard = cw.sprite.card.PlayerCard(data, pos_noscale=pos_noscale, status="deal", index=index)
        pcard.restore_personalpocket()
        cw.animation.animate_sprite(pcard, "deal")

    def remove(self, pcard: "cw.sprite.card.PlayerCard") -> None:
        """
        メンバーを削除する。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        pcard.remove_numbercoupon()
        if pcard.personal_pocket:
            pcard.store_personalpocket()
        self.members.remove(pcard.data)
        if cw.cwpy.cardgrp.has(pcard):
            pcard.hide()
            cw.cwpy.cardgrp.remove(pcard)
            cw.cwpy.pcards.remove(pcard)
        e_members = self.data.find("Property/Members")
        if e_members is not None:
            e_members.clear()

        for pcard in cw.cwpy.get_pcards():
            s = os.path.basename(pcard.data.fpath)
            s = cw.util.splitext(s)[0]
            e = self.data.make_element("Member", s)
            self.data.append("Property/Members", e)

    def replace_order(self, index1: int, index2: int) -> None:
        """
        メンバーの位置を入れ替える。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        seq = cw.cwpy.get_pcards()
        assert len(seq) == len(self.members)
        seq[index1], seq[index2] = seq[index2], seq[index1]
        seq[index1].index, seq[index2].index = seq[index2].index, seq[index1].index
        self.members[index1], self.members[index2] = self.members[index2], self.members[index1]
        for pcard in seq:
            pcard.tlayer = (pcard.tlayer[0], pcard.tlayer[1], pcard.index, pcard.tlayer[3])
            cw.cwpy.cardgrp.change_layer(pcard, cw.layer_val(pcard.tlayer))
            pcard.update_personalownerindex()
        cw.cwpy.pcards = seq

        e_members = self.data.find("Property/Members")
        if e_members is not None:
            e_members.clear()
        for pcard in cw.cwpy.get_pcards():
            s = os.path.basename(pcard.data.fpath)
            s = cw.util.splitext(s)[0]
            e = self.data.make_element("Member", s)
            self.data.append("Property/Members", e)

        pcard1 = seq[index1]
        pcard2 = seq[index2]
        cw.animation.animate_sprites([pcard1, pcard2], "hide")
        pos_noscale = seq[index1].get_pos_noscale()
        seq[index1].set_pos_noscale(seq[index2].get_pos_noscale())
        seq[index2].set_pos_noscale(pos_noscale)
        cw.animation.animate_sprites([pcard1, pcard2], "deal")

    def set_name(self, name: str) -> None:
        """
        パーティ名を変更する。
        """
        if self.name != name:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            oldname = self.name
            self.name = name
            self.data.edit("Property/Name", name)
            cw.cwpy.advlog.rename_party(self.name, oldname)
            cw.cwpy.background.reload(False, nocheckvisible=True)

    def set_money(self, value: int, fromevent: bool = False, blink: bool = False) -> None:
        """
        パーティの所持金を変更する。
        """
        if value != 0:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.money += value
            self.money = cw.util.numwrap(self.money, 0, 9999999)
            self.data.edit("Property/Money", str(self.money))
            if blink:
                if cw.cwpy.statusbar.partymoney:
                    cw.animation.start_animation(cw.cwpy.statusbar.partymoney, "blink")
            if not fromevent:
                showbuttons = not cw.cwpy.is_playingscenario() or not cw.cwpy.is_runningevent()
                cw.cwpy.statusbar.change(showbuttons)
                cw.cwpy.has_inputevent = True

    def suspend_levelup(self, suspend: bool) -> None:
        """
        レベルアップの可否を設定する。
        """
        if suspend != self.is_suspendlevelup:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.is_suspendlevelup = suspend
            e = self.data.find("Property/SuspendLevelUp")
            if e is None:
                pe = self.data.find_exists("Property")
                pe.append(make_element("SuspendLevelUp", str(suspend)))
                self.data.is_edited = True
            else:
                self.data.edit("Property/SuspendLevelUp", str(suspend))

    def set_numbercoupon(self) -> None:
        """
        番号クーポンを配布する。
        """
        names = [cw.cwpy.msgs["number_1_coupon"], "＿２", "＿３", "＿４", "＿５", "＿６"]

        for index, pcard in enumerate(cw.cwpy.get_pcards()):
            pcard.remove_numbercoupon()
            pcard.set_coupon(names[index], 0)
            if pcard.level < pcard.get_limitlevel():
                pcard.set_coupon("：レベル補正中", 0)  # 1.28
            pcard.set_coupon("＠ＭＰ３", 0)  # 1.29

    def remove_numbercoupon(self) -> None:
        """
        番号クーポンを除去する。
        """
        for pcard in cw.cwpy.get_pcards():
            pcard.remove_numbercoupon()

    def write(self) -> None:
        self.data.write_xml()

        for member in self.members:
            member.write_xml()

    def lost(self) -> None:
        """ゲームオーバー時にパーティ全体を破棄する。
        """
        assert cw.cwpy.ydata
        cw.cwpy.ydata.changed()
        for pcard in cw.cwpy.get_pcards():
            pcard.lost()
        self.members = []

        for card in self.backpack[:]:
            cw.cwpy.trade("TRASHBOX", header=card, from_event=True, sort=False, party=self)

        cw.cwpy.remove_xml(self)
        cw.cwpy.ydata.deletedpaths.add(os.path.dirname(self.path))

    def get_coupontable(self) -> Dict[str, int]:
        """
        パーティ全体が所持しているクーポンの
        所持数テーブルを返す。
        """
        d: Dict[str, int] = {}

        for member in self.members:
            for e in member.getfind("Property/Coupons"):
                if e.text in d:
                    d[e.text] += 1
                else:
                    d[e.text] = 1

        return d

    def get_coupons(self) -> Set[str]:
        """
        パーティ全体が所持しているクーポンをセット型で返す。
        """
        seq = []

        for member in self.members:
            for e in member.getfind("Property/Coupons"):
                seq.append(e.text)

        return set(seq)

    def get_allcardheaders(self) -> List["cw.header.CardHeader"]:
        seq: List[cw.header.CardHeader] = []
        seq.extend(self.backpack)

        for pcard in cw.cwpy.get_pcards():
            for headers in pcard.cardpocket:
                seq.extend(headers)

        return seq

    def is_adventuring(self) -> bool:
        path = cw.util.splitext(self.data.fpath)[0] + ".wsl"
        return bool(cw.util.get_yadofilepath(path))

    def get_sceheader(self) -> Optional["cw.header.ScenarioHeader"]:
        """
        現在冒険中のシナリオのScenarioHeaderを返す。
        """
        path = cw.util.splitext(self.data.fpath)[0] + ".wsl"
        path = cw.util.get_yadofilepath(path)

        if path:
            e = cw.util.get_elementfromzip(path, "ScenarioLog.xml", "Property")
            path = e.gettext("WsnPath", "")
            db = cw.scenariodb.Scenariodb()
            sceheader: Optional[cw.header.ScenarioHeader] = db.search_path(path)
            db.close()
            return sceheader
        else:
            return None

    def get_memberpaths(self) -> List[str]:
        """
        現在選択中のパーティのメンバーのxmlのpathリストを返す。
        """
        cw.fsync.sync()
        seq = []

        for e in self.data.getfind("Property/Members"):
            if e.text:
                path = cw.util.join_yadodir(cw.util.join_paths("Adventurer",  e.text + ".xml"))
                if not os.path.isfile(path):
                    # Windowsがファイル名を変えるため前後のスペースを除く
                    path = cw.util.join_yadodir(cw.util.join_paths("Adventurer", e.text.strip() + ".xml"))

                seq.append(path)

        return seq

    def set_lastscenario(self, lastscenario: List[str], lastscenariopath: str) -> None:
        """
        プレイ中シナリオへの経路を記録する。
        """
        self.lastscenario = lastscenario
        self.lastscenariopath = lastscenariopath
        e = self.data.find("Property/LastScenario")
        if e is None:
            e = make_element("LastScenario")
            self.data.append("Property", e)

        e.clear()
        self.data.edit("Property/LastScenario", lastscenariopath, "path")
        for path in lastscenario:
            self.data.append("Property/LastScenario", make_element("Path", path))


def sort_cards(cards: List["cw.header.CardHeader"], condition: str, withstar: bool) -> None:
    seq = ["personal_owner_index"] if cw.cwpy.setting.show_personal_cards else []
    if withstar:
        seq.append("negastar")

    def addetckey() -> None:
        for key in ("name", "scenario", "author", "type_id", "level", "sellingprice"):
            if key != seq[0]:
                seq.append(key)

    if condition == "Level":
        seq.append("level")
        addetckey()
    elif condition == "Name":
        seq.append("name")
        addetckey()
    elif condition == "Type":
        seq.append("type_id")
        addetckey()
    elif condition == "Price":
        seq.append("sellingprice")
        addetckey()
    elif condition == "Scenario":
        seq.append("scenario")
        addetckey()
    elif condition == "Author":
        seq.append("author")
        addetckey()
    elif condition == "Aptitude":
        seq.append("vocation_for_sort")
    seq.append("order")

    cw.util.sort_by_attr(cards, *seq)


# ------------------------------------------------------------------------------
# CWPyElement
# ------------------------------------------------------------------------------

class _CWPyElementInterface(object):
    fpath: str

    def _raiseerror(self, path: str, attr: str = "") -> NoReturn:
        if isinstance(self, CWPyElement):
            tag = self.tag + "/" + path
        elif isinstance(self, CWPyElementTree):
            tag = self.getroot().tag + "/" + path
        else:
            tag = path

        s = 'Invalid XML! (file="%s", tag="%s", attr="%s")'
        s = s % (self.fpath, tag, attr)
        raise ValueError(s)

    def find(self, match: str) -> Optional["CWPyElement"]:
        return None

    def hasfind(self, path: str, attr: str = "") -> bool:
        e = self.find(path)

        if attr:
            return bool(e is not None and attr in e.attrib)
        else:
            return bool(e is not None)

    def getfind(self, path: str, raiseerror: bool = True) -> Union["CWPyElement", Sequence["CWPyElement"]]:
        e = self.find(path)

        if e is None:
            if raiseerror:
                self._raiseerror(path)
            return ()

        return e

    def gettext(self, path: str, default: Optional[str] = None) -> str:
        e = self.find(path)

        if e is None:
            text = default
        else:
            text = e.text
            if text is None:
                text = ""

        if text is None:
            self._raiseerror(path)

        return text

    def getattr(self, path: str, attr: str, default: Optional[str] = None) -> str:
        e = self.find(path)

        if e is None or attr not in e.attrib:
            text = default
        else:
            text = e.get(attr)

        if text is None:
            self._raiseerror(path, attr)

        return text

    def getbool(self, path: str, attr: Optional[Union[str, bool]] = None, default: Optional[bool] = None) -> bool:
        if isinstance(attr, bool):
            default = attr
            attr = ""
            s = self.gettext(path, "")
            if s == "":
                return default
        elif attr:
            s = self.getattr(path, attr, "")
            if s == "":
                if default is None:
                    self._raiseerror(path, str(attr))
                return default
        else:
            s = self.gettext(path, "")
            if s == "":
                if default is None:
                    self._raiseerror(path, str(attr))
                return default

        try:
            return cw.util.str2bool(s)
        except Exception:
            self._raiseerror(path, str(attr))

    def getint(self, path: str, attr: Optional[Union[int, str]] = None, default: Optional[int] = None) -> int:
        if isinstance(attr, int):
            default = attr
            attr = ""
            s = self.gettext(path, "")
            if s == "":
                return default
        elif attr:
            s = self.getattr(path, attr, "")
            if s == "":
                if default is None:
                    self._raiseerror(path, str(attr))
                return default
        else:
            s = self.gettext(path, "")
            if s == "":
                if default is None:
                    self._raiseerror(path, str(attr))
                return default

        try:
            return int(float(s))
        except Exception:
            self._raiseerror(path, str(attr))

    def getfloat(self, path: str, attr: Optional[Union[str, float]] = None, default: Optional[float] = None) -> float:
        if isinstance(attr, float):
            default = attr
            attr = ""
            s = self.gettext(path, "")
            if s == "":
                return default
        elif attr:
            s = self.getattr(path, attr, "")
            if s == "":
                if default is None:
                    self._raiseerror(path, str(attr))
                return default
        else:
            s = self.gettext(path, "")
            if s == "":
                if default is None:
                    self._raiseerror(path, str(attr))
                return default

        try:
            return float(s)
        except Exception:
            self._raiseerror(path, str(attr))

    def make_element(self, name: str, text: str = "", attrs: Optional[Dict[str, str]] = None,
                     tail: str = "") -> "CWPyElement":
        return make_element(name, text, attrs, tail)


class _ElementWrapper(xml.etree.cElementTree.Element):
    def __init__(self, wrap: "CWPyElement", tag: str, attrib: Dict[str, str]) -> None:
        xml.etree.cElementTree.Element.__init__(self, tag, attrib)
        self.wrap = wrap


class CWPyElement(_CWPyElementInterface, Sequence["CWPyElement"]):
    def __init__(self, tag: str, attrib: Optional[Dict[str, str]] = None) -> None:
        if attrib is None:
            attrib = {}
        self.element = _ElementWrapper(self, tag, attrib)

        self.fpath = ""

        self._iter = 0

        # CWXパスを構築するための親要素情報
        self.cwxparent: Optional[CWPyElement] = None
        self.content: Optional[cw.content.EventContentBase] = None
        self.nextelements: Optional[List[CWPyElement]] = None
        self.needcheck: Optional[bool] = None
        self.cwxpath: Optional[str] = None
        self._cwxline_index: Optional[int] = None

    @property
    def tag(self) -> str:
        return self.element.tag

    @tag.setter
    def tag(self, tag: str) -> None:
        self.element.tag = tag

    def find(self, path: str) -> Optional["CWPyElement"]:
        e = self.element.find(path)
        if e is None:
            return None
        return typing.cast(_ElementWrapper, e).wrap

    def find_exists(self, path: str) -> "CWPyElement":
        e = self.find(path)
        if e is None:
            tag = self.tag
            parent = self
            while True:
                if parent.cwxparent is None:
                    break
                parent = parent.cwxparent
                tag = parent.tag + "/" + tag
            raise ValueError("%s:%s:%s is not found." % (parent.fpath, tag, path))
        return e

    @property
    def attrib(self) -> Dict[str, str]:
        return self.element.attrib

    @property
    def text(self) -> str:
        return self.element.text if self.element.text is not None else ""

    @text.setter
    def text(self, text: str) -> None:
        self.element.text = text

    @property
    def tail(self) -> str:
        return self.element.tail if self.element.tail is not None else ""

    @tail.setter
    def tail(self, tail: str) -> None:
        self.element.tail = tail

    def get(self, key: str, defaultvalue: str = "") -> str:
        return self.element.get(key, defaultvalue)

    def set(self, key: str, value: str) -> None:
        self.element.set(key, value)

    def keys(self) -> KeysView[str]:
        return self.element.keys()

    def items(self) -> ItemsView[str, str]:
        return self.element.items()

    def append(self, subelement: "CWPyElement") -> None:
        subelement.cwxparent = self
        self.element.append(subelement.element)

    def extend(self, subelements: Iterable["CWPyElement"]) -> None:
        for subelement in subelements:
            subelement.cwxparent = self
        self.element.extend(map(lambda e: e.element, subelements))

    def insert(self, index: int, subelement: "CWPyElement") -> None:
        subelement.cwxparent = self
        self.element.insert(index, subelement.element)

    def remove(self, subelement: "CWPyElement") -> None:
        assert subelement.cwxparent is self
        subelement.cwxparent = None
        self.element.remove(subelement.element)

    def clear(self) -> None:
        for subelement in self:
            subelement.cwxparent = None
        self.element.clear()

    def index(self, subelement: "CWPyElement", start: Optional[int] = None, end: Optional[int] = None) -> int:
        if start is None:
            start = 0
        if end is None:
            end = len(self)
        for i in range(start, end):
            if self[i] == subelement:
                return i
        return -1

    def get_cwxpath(self) -> str:
        """CWXパスを構築して返す。
        イベントまたはその親要素でなければ正しいパスは構築されない。
        """
        if self.cwxpath is not None:
            return self.cwxpath

        cwxpath = []

        e: CWPyElement = self
        scenariodata = False
        while True:
            if "cwxpath" in e.attrib:
                # 召喚獣召喚効果で付与された召喚獣
                cwxpath.append(e.attrib.get("cwxpath", ""))
                scenariodata = True
                break
            elif e.tag == "Area":
                cwxpath.append("area:id:%s" % (e.gettext("Property/Id", "0")))
                scenariodata = True
            elif e.tag == "Battle":
                cwxpath.append("battle:id:%s" % (e.gettext("Property/Id", "0")))
                scenariodata = True
            elif e.tag == "Package":
                cwxpath.append("package:id:%s" % (e.gettext("Property/Id", "0")))
                scenariodata = True
            elif e.tag == "CastCard":
                cwxpath.append("castcard:id:%s" % (e.gettext("Property/Id", "0")))
                scenariodata = True
                break
            elif e.tag == "SkillCard":
                cwxpath.append("skillcard:id:%s" % (e.gettext("Property/Id", "0")))
                if e.getbool(".", "scenariocard", False):
                    scenariodata = True
                    break
            elif e.tag == "ItemCard":
                cwxpath.append("itemcard:id:%s" % (e.gettext("Property/Id", "0")))
                if e.getbool(".", "scenariocard", False):
                    scenariodata = True
                    break
            elif e.tag == "BeastCard":
                cwxpath.append("beastcard:id:%s" % (e.gettext("Property/Id", "0")))
                if e.getbool(".", "scenariocard", False):
                    scenariodata = True
                    break
            elif e.tag in ("MenuCard", "LargeMenuCard"):
                if e.cwxparent is None:
                    raise ValueError(e.tag)
                cwxpath.append("menucard:%s" % (e.cwxparent.index(e)))
            elif e.tag == "EnemyCard":
                if e.cwxparent is None:
                    raise ValueError(e.tag)
                cwxpath.append("enemycard:%s" % (e.cwxparent.index(e)))
            elif e.tag == "Event":
                if e.cwxparent is None:
                    raise ValueError(e.tag)
                cwxpath.append("event:%s" % (e.cwxparent.index(e)))
            elif e.tag == "Motion":
                if e.cwxparent is None:
                    raise ValueError(e.tag)
                cwxpath.append("motion:%s" % (e.cwxparent.index(e)))
            elif e.tag in ("SkillCards", "ItemCards", "BeastCards", "Beasts", "Motions",
                           "Contents", "Events", "MenuCards", "EnemyCards"):
                pass
            elif e.tag in ("Adventurer", "CastCards", "System", "ActionCard"):
                break
            elif e.tag == "PlayerCardEvents":
                # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
                if e.cwxparent is None:
                    raise ValueError(e.tag)
                cwxpath.append("playercard:%s" % (e.cwxparent.index(e)))
            else:
                # Content
                if e.cwxparent is None:
                    raise ValueError(e.tag)
                if e.cwxparent.tag not in ("Contents", "ContentsLine"):
                    raise ValueError(e.cwxparent.tag + "/" + e.tag)
                if e.cwxparent.tag == "ContentsLine":
                    if e._cwxline_index is None:
                        parent: CWPyElement = e.cwxparent
                        for i, line_child in enumerate(parent):
                            assert isinstance(line_child, CWPyElement)
                            line_child._cwxline_index = i
                    assert e._cwxline_index is not None
                    for _i in range(e._cwxline_index):
                        cwxpath.append(":0")
                else:
                    cwxpath.append(":%s" % (e.cwxparent.index(e)))

            if e.cwxparent is None:
                break
            e = e.cwxparent

        if scenariodata:
            self.cwxpath = "/".join(reversed(cwxpath))
        else:
            self.cwxpath = ""

        assert self.cwxpath is not None
        return self.cwxpath

    def iter(self, tag: Optional[str] = None) -> Generator["CWPyElement", None, None]:
        if tag is None or self.tag == tag:
            yield self
        for e in self:
            yield from e.iter(tag)

    def __repr__(self) -> str:
        return self.element.__repr__()

    def __len__(self) -> int:
        return self.element.__len__()

    def __bool__(self) -> bool:
        raise ValueError()

    @typing.overload
    def __getitem__(self, index: int) -> "CWPyElement": ...

    @typing.overload
    def __getitem__(self, index: slice) -> Sequence["CWPyElement"]: ...

    def __getitem__(self, index: Union[int, slice]) -> Union["CWPyElement", Sequence["CWPyElement"]]:
        if isinstance(index, int):
            e = self.element.__getitem__(index)
            return typing.cast(_ElementWrapper, e).wrap
        else:
            assert isinstance(index, slice)
            return [typing.cast(_ElementWrapper, e).wrap for e in self.element.__getitem__(index)]

    def __setitem__(self, index: int, element: "CWPyElement") -> None:
        e = self[index]
        assert isinstance(e, CWPyElement)
        if element.cwxparent is not self:
            # self[index1], self[index2] = self[index2], self[index1]
            # のようなケースでe.cwxparentをNoneにするとself[index2].cwxparentが消えてしまう
            e.cwxparent = None
        element.cwxparent = self
        self.element.__setitem__(index, element.element)

    def __delitem__(self, index: Union[int, slice]) -> None:
        if isinstance(index, int):
            e = self[index]
            assert isinstance(e, CWPyElement)
            e.cwxparent = None
        else:
            assert isinstance(index, slice)
            for e in self[index]:
                e.cwxparent = None
        self.element.__delitem__(index)

    def __iter__(self) -> Iterator["CWPyElement"]:
        return _CWPyElementIterator(self)

    def __reversed__(self) -> Generator["CWPyElement", None, None]:
        for i in range(len(self), 0, -1):
            yield self[i - 1]


class _CWPyElementIterator(object):
    def __init__(self, e: CWPyElement) -> None:
        self.e = e
        self._iter = 0

    def __iter__(self) -> Iterator["CWPyElement"]:
        self._iter = 0
        return _CWPyElementIterator(self.e)

    def __next__(self) -> "CWPyElement":
        if self._iter < 0 or len(self.e) <= self._iter:
            raise StopIteration()
        n = self.e[self._iter]
        self._iter += 1
        return n


# ------------------------------------------------------------------------------
# CWPyElementTree
# ------------------------------------------------------------------------------

class CWPyElementTree(_CWPyElementInterface):
    def __init__(self, fpath: str = "", element: Optional[CWPyElement] = None) -> None:
        if element is None:
            element = xml2element(fpath)

        self._etree = ElementTree(element=element.element)
        self._root = element
        self.fpath = element.fpath
        self.is_edited = False

    def getroot(self) -> CWPyElement:
        return self._root

    def iter(self) -> Generator[CWPyElement, None, None]:
        return self._root.iter()

    def find(self, path: str) -> Optional[CWPyElement]:
        return self._root.find(path)

    def find_exists(self, path: str) -> "CWPyElement":
        return self._root.find_exists(path)

    def write_bytes(self) -> bytes:
        # インデント整形
        self.form_element(self.getroot())
        with io.BytesIO() as f:
            f.write('<?xml version="1.0" encoding="utf-8" ?>\n'.encode("utf-8"))
            self._etree.write(f, "utf-8")
            sbytes = f.getvalue()
            f.close()
        return sbytes

    def write_file(self, path: str = "") -> None:
        if not path:
            path = self.fpath

        # 書き込み
        dpath = os.path.dirname(path)

        if dpath and not os.path.isdir(dpath):
            os.makedirs(dpath)

        cw.util.write_file(path, self.write_bytes(), cw.fsync)

    def write_xml(self, nocheck_edited: bool = False) -> None:
        """エレメントが編集されていたら、
        "Data/Temp/Yado"にxmlファイルを保存。
        """
        if self.is_edited or nocheck_edited:
            if not self.fpath.startswith(cw.cwpy.tempdir):
                fpath = self.fpath.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)
                self.fpath = fpath

            self.write_file(self.fpath)
            self.is_edited = False

    def edit(self, path: str, value: str, attrname: Optional[str] = None) -> None:
        """パスのエレメントを編集。"""
        if not isinstance(value, str):
            try:
                value = str(value)
            except Exception:
                cw.util.print_ex(file=sys.stderr)
                sys.stderr.write("エレメント編集失敗 (%s, %s, %s, %s)\n" % (self.fpath, path, value, attrname))
                return

        e = self.find(path)
        if e is None:
            raise ValueError(path)
        if attrname:
            e.set(attrname, value)
        else:
            e.text = value

        self.is_edited = True

    def append(self, path: str, element: CWPyElement) -> None:
        e = self.find(path)
        if e is None:
            raise ValueError(path)
        e.append(element)
        self.is_edited = True

    def insert(self, path: str, element: CWPyElement, index: int) -> None:
        """パスのエレメントの指定位置にelementを挿入。
        indexがNoneの場合はappend()の挙動。
        """
        e = self.find(path)
        if e is None:
            raise ValueError(path)
        e.insert(index, element)
        self.is_edited = True

    def remove(self, path: str, element: Optional[CWPyElement] = None, attrname: Optional[str] = None) -> None:
        """パスのエレメントからelementを削除した後、
        CWPyElementTreeのインスタンスで返す。
        """
        e = self.find(path)
        if e is None:
            raise ValueError(path)
        if attrname:
            e.get(attrname)  # 属性の辞書を生成させる
            del e.attrib[attrname]
        else:
            assert element is not None
            e.remove(element)
        self.is_edited = True

    def form_element(self, element: CWPyElement, depth: int = 0) -> None:
        """elementのインデントを整形"""
        i = "\n" + " " * depth

        if len(element):
            if not element.text:
                element.text = i + " "

            if not element.tail:
                element.tail = i if depth else ""

            for element in element:
                self.form_element(element, depth + 1)

            if not element.tail:
                element.tail = i

        else:
            if not element.text:
                element.text = ""

            if not element.tail:
                element.tail = i if depth else ""


# ------------------------------------------------------------------------------
# xmlパーサ
# ------------------------------------------------------------------------------

def make_element(name: str, text: str = "", attrs: Optional[Dict[str, str]] = None, tail: str = "") -> CWPyElement:
    if attrs is None:
        attrs = {}
    element = CWPyElement(name, attrs)
    element.text = text
    element.tail = tail
    return element


def yadoxml2etree(path: str, tag: str = "", rootattrs: Optional[Dict[str, str]] = None) -> CWPyElementTree:
    element = yadoxml2element(path, tag, rootattrs=rootattrs)
    return CWPyElementTree(element=element)


def yadoxml2element(path: str, tag: str = "", rootattrs: Optional[Dict[str, str]] = None) -> CWPyElement:
    yadodir = cw.util.join_paths(cw.tempdir, "Yado")
    if path.startswith("Yado"):
        temppath = path.replace("Yado", yadodir, 1)
    elif path.startswith(yadodir):
        temppath = path
        path = path.replace(yadodir, "Yado", 1)
    else:
        raise ValueError("%s is not YadoXMLFile." % path)

    if temppath and cw.fsync.is_waiting(temppath):
        cw.fsync.sync()
    elif path and cw.fsync.is_waiting(path):
        cw.fsync.sync()

    if os.path.isfile(temppath):
        return xml2element(temppath, tag, rootattrs=rootattrs)
    elif os.path.isfile(path):
        return xml2element(path, tag, rootattrs=rootattrs)
    else:
        raise ValueError("%s is not found." % path)


def xml2etree(path: str = "", tag: str = "", stream: Optional[BinaryIO] = None,
              element: Optional[CWPyElement] = None, nocache: bool = False) -> CWPyElementTree:
    if element is None:
        element = xml2element(path, tag, stream, nocache=nocache)

    return CWPyElementTree(element=element)


def xml2element(path: str = "", tag: str = "", stream: Optional[BinaryIO] = None, nocache: bool = False,
                rootattrs: Optional[Dict[str, str]] = None) -> CWPyElement:
    usecache = path and cw.cwpy and cw.cwpy.sdata and\
               isinstance(cw.cwpy.sdata, cw.data.ScenarioData) and\
               path.startswith(cw.cwpy.sdata.tempdir)
    if path and cw.fsync.is_waiting(path):
        cw.fsync.sync()

    if usecache:
        mtime = os.path.getmtime(path)

    # キャッシュからデータを取得
    if usecache:
        assert cw.cwpy.sdata
        if path in cw.cwpy.sdata.data_cache:
            cachedata = cw.cwpy.sdata.data_cache[path]
            if mtime <= cachedata.mtime:
                data: Optional[CWPyElement] = cachedata.data
                assert data is not None
                if rootattrs is not None:
                    for key, value in data.attrib.items():
                        rootattrs[key] = value
                if tag:
                    data = data.find(tag)
                    if data is None:
                        raise ValueError(path + ": " + tag)
                if nocache:
                    # 変更されてもよいデータを返す
                    return copydata(data)
                return data

    data = None
    versionhint: Optional[Tuple[str, str, bool, bool, bool]] = None
    if not stream and cw.cwpy and cw.cwpy.classicdata:
        # クラシックなシナリオのファイルだった場合は変換する
        lpath = path.lower()
        if lpath.endswith(".wsm") or lpath.endswith(".wid"):
            cdata, filedata = cw.cwpy.classicdata.load_file(path)
            if cdata is None:
                raise ValueError(path + ": " + tag)
            data = cdata.get_data()
            data.fpath = path

            # 互換性マーク付与
            versionhint = cw.cwpy.sct.get_versionhint(filedata=filedata)
            if cw.cwpy.classicdata.hasmodeini:
                # mode.ini優先
                versionhint = cw.cwpy.sct.merge_versionhints(cw.cwpy.classicdata.versionhint, versionhint)
            else:
                if not versionhint:
                    # 個別のファイルの情報が無い場合はシナリオの情報を使う
                    versionhint = cw.cwpy.classicdata.versionhint

    if data is None:
        if not usecache and tag and not versionhint:
            parser = SimpleXmlParser(path, tag, stream, targetonly=True, rootattrs=rootattrs)
            return parser.parse()
        else:
            parser = SimpleXmlParser(path, "", stream)
            data = parser.parse()
    assert data is not None

    basedata = data
    if rootattrs is not None:
        for key, value in data.attrib.items():
            rootattrs[key] = value
    if tag:
        data = data.find(tag)
        if data is None:
            raise ValueError(path + ": " + tag)

    if usecache:
        # キャッシュにデータを保存
        assert cw.cwpy.sdata
        cachedata = CacheData(basedata, mtime)
        cw.cwpy.sdata.data_cache[path] = cachedata
        if nocache:
            data = copydata(data)

    if cw.cwpy and versionhint:
        basehint = cw.cwpy.sct.to_basehint(versionhint)
        if basehint:
            prop = data.find("Property")
            if prop is not None:
                prop.set("versionHint", basehint)

    return data


class CacheData(object):
    def __init__(self, data: CWPyElement, mtime: float) -> None:
        self.data = data
        self.mtime = mtime


def copydata(data: CWPyElement, copyall: bool = False) -> CWPyElement:
    if not copyall and data.tag in ("Motions", "Events", "Id", "Name",
                                    "Description", "Scenario", "Author", "Level", "Ability",
                                    "Target", "EffectType", "ResistType", "SuccessRate",
                                    "VisualEffect", "KeyCodes", "Premium",
                                    "EnhanceOwner", "Price"):
        # 不変
        return data

    e = make_element(data.tag, data.text, copy.deepcopy(data.attrib), data.tail)
    for child in data:
        e.append(copydata(child))

    e.cwxparent = data.cwxparent
    e.content = data.content
    e.nextelements = data.nextelements
    e.needcheck = data.needcheck

    return e


def copytree(data: CWPyElementTree, copyall: bool = False) -> CWPyElementTree:
    return CWPyElementTree(element=copydata(data.getroot(), copyall))


class EndTargetTagException(Exception):
    pass


class SimpleXmlParser(object):
    def __init__(self, fpath: str, targettag: str = "", stream: Optional[BinaryIO] = None, targetonly: bool = False,
                 rootattrs: Optional[Dict[str, str]] = None) -> None:
        """
        targettag: 読み込むタグのロケーションパス。絶対パスは使えない。
            "Property/Name"という風にタグごとに"/"で区切って指定する。
            targettagが空の場合は、全てのデータを読み込む。
        """
        self.fpath = fpath.replace("\\", "/")
        self.targettag = targettag.strip("/")
        self.file = stream
        self.targetonly = targetonly
        self.rootattrs = rootattrs
        self._clear_attrs()

    def _clear_attrs(self) -> None:
        self.root: Optional[CWPyElement] = None
        self.node_stack: List[CWPyElement] = []
        self.parsetags: List[str] = []
        self.currenttags: List[str] = []
        if self.rootattrs:
            self.rootattrs.clear()
        self._persed = False

    def start_element(self, name: str, attrs: Dict[str, str]) -> None:
        """要素の開始。"""
        if not self.currenttags:
            if self.rootattrs is not None:
                for key, value in attrs.items():
                    self.rootattrs[key] = value

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
                for key, value in attrs.items():
                    element.attrib[key] = value
                self.root = element

            self.node_stack.append(element)

    def end_element(self, name: str) -> None:
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

    def char_data(self, data: str) -> None:
        """文字データ"""
        if self.parsetags:
            if data:
                element = self.node_stack[-1]

                if not len(element):
                    if element.text:
                        element.text += data
                    else:
                        element.text = data

    def parse(self) -> CWPyElement:
        if self.file and hasattr(self.file, "read"):
            self.parse_file(self.file)
        else:
            with open(self.fpath, "rb") as f:
                self.parse_file(f)
                f.close()

        assert self.root is not None
        return self.root

    def parse_file(self, fname: BinaryIO) -> None:
        try:
            self._parse_file(fname)
        except EndTargetTagException:
            pass
        except xml.parsers.expat.ExpatError as err:
            # エラーになったファイルのパスを付け加える
            s = ". file: " + self.fpath
            err.args = (err.args[0] + s, )
            raise err

    def _create_parser(self) -> xml.parsers.expat.XMLParserType:
        parser = xml.parsers.expat.ParserCreate()
        parser.buffer_text = True
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.char_data
        return parser

    def _parse_file(self, fname: BinaryIO) -> None:
        parser = self._create_parser()
        fdata_b = fname.read()
        try:
            parser.Parse(fdata_b, True)
        except xml.parsers.expat.ExpatError:
            # たまに制御文字が混入しているシナリオがある
            fdata = str(fdata_b, "utf-8", "ignore")
            fdata = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", fdata)
            fdata_b = fdata.encode("utf-8")
            self._clear_attrs()
            parser = self._create_parser()
            parser.Parse(fdata_b, True)

    def get_currentpath(self) -> str:
        if len(self.currenttags) > 1:
            return "/".join(self.currenttags[1:])
        else:
            return ""


def main() -> None:
    pass


if __name__ == "__main__":
    main()
