#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import io
import re
import copy
import time
import shutil
import threading
import ctypes
import xml.parsers.expat
from xml.etree.cElementTree import ElementTree
from xml.etree.ElementTree import _ElementInterface

import pygame

import cw
from cw.util import synclock


_lock = threading.Lock()

_WSN_DATA_DIRS = ("area", "battle", "package", "castcard", "skillcard", "itemcard", "beastcard", "infocard")


#-------------------------------------------------------------------------------
#　システムデータ
#-------------------------------------------------------------------------------

class SystemData(object):
    def __init__(self):
        """
        引数のゲームの状態遷移の情報によって読み込むxmlを変える。
        """
        cw.cwpy.debug = cw.cwpy.setting.debug
        self.wsn_version = ""
        self.data = None
        self.name = ""
        self.sdata = ""
        self.author = ""
        self.fpath = ""
        self.mtime = 0
        self.tempdir = ""
        self.scedir = ""

        self._areas = {}
        self._battles = {}
        self._packs = {}
        self._casts = {}
        self._infos = {}
        self._items = {}
        self._skills = {}
        self._beasts = {}

        self._init_xmlpaths()
        self._init_sparea_mcards()

        self.is_playing = True
        self.events = None
        self.playerevents = None # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
        self.deletedpaths = set()
        self.lostadventurers = set()
        self.gossips = {}
        self.compstamps = {}
        self.friendcards = []
        self.infocards = []
        self.infocard_maxindex = 0
        self._infocard_cache = {}
        self.flags = {}
        self.steps = {}
        self.labels = {}
        self.ignorecase_table = {}
        self.notice_infoview = False
        self.infocards_beforeevent = None
        self.pre_battleareadata = None
        self.data_cache = {}
        self.resource_cache = {}
        self.resource_cache_size = 0
        self.autostart_round = False
        self.breakpoints = set()
        self.in_f9 = False
        self.in_endprocess = False
        self.background_image_mtime = {}

        # "file.x2.bmp"などのスケーリングされたイメージを読み込むか
        self.can_loaded_scaledimage = True

        # メッセージのバックログ
        self.backlog = []
        # キャンプ中に移動したカードの使用回数の記憶
        self.uselimit_table = {}

        # シナリオごとのブレークポイントを保存する
        if isinstance(cw.cwpy.sdata, ScenarioData):
            cw.cwpy.sdata.save_breakpoints()

        # refresh debugger
        self._init_debugger()

    def _init_debugger(self):
        cw.cwpy.event.refresh_variablelist()

    def update_skin(self):
        self._init_xmlpaths()
        self._init_sparea_mcards()

    def _init_xmlpaths(self, xmlonly=False):
        self._areas.clear()
        self._battles.clear()
        self._packs.clear()
        self._casts.clear()
        self._infos.clear()
        self._items.clear()
        self._skills.clear()
        self._beasts.clear()
        dpaths = (cw.util.join_paths(cw.cwpy.skindir, u"Resource/Xml", cw.cwpy.status),
                  cw.util.join_paths(u"Data/SkinBase/Resource/Xml", cw.cwpy.status))

        for dpath in dpaths:
            for fname in os.listdir(dpath):
                path = cw.util.join_paths(dpath, fname)

                if os.path.isfile(path) and fname.endswith(".xml"):
                    e = xml2element(path, "Property")
                    resid = e.getint("Id")
                    name = e.gettext("Name")
                    if not resid in self._areas:
                        self._areas[resid] = (name, path)

    def _init_sparea_mcards(self):
        """
        カード移動操作エリアのメニューカードを作成する。
        エリア移動時のタイムラグをなくすための操作。
        """
        d = {}

        for key in self._areas.iterkeys():
            if key in cw.AREAS_TRADE:
                data = self.get_mcarddata(key, battlestatus=False)
                areaid = cw.cwpy.areaid
                cw.cwpy.areaid = key
                mcards = cw.cwpy.set_mcards(data, False, addgroup=False, setautospread=False)
                cw.cwpy.areaid = areaid
                d[key] = mcards

        self.sparea_mcards = d

    def is_wsnversion(self, wsn_version, cardversion=None):
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
            except:
                return False

    def get_versionhint(self, frompos=0):
        """現在有効になっている互換性マークを返す(常に無し)。"""
        return None

    def set_versionhint(self, pos, hint):
        """互換性モードを設定する(処理無し)。"""
        pass

    def update_scale(self):
        for mcards in self.sparea_mcards.itervalues():
            for mcard in mcards:
                mcard.update_scale()
        for log in self.backlog:
            if log.specialchars:
                log.specialchars.reset()

    def sweep_resourcecache(self, size):
        """新しくキャッシュを追加した時にメモリが不足しそうであれば
        これまでのキャッシュをクリアする。
        """
        # 使用可能なヒープサイズの半分までをキャッシュに使用する"
        if sys.platform == "win32":
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

    def start(self):
        pass

    def end(self):
        pass

    def save_breakpoints(self):
        pass

    def set_log(self):
        """
        wslファイルの読み込みまたは新規作成を行う。
        読み込みを行った場合はTrue、新規作成を行った場合はFalseを返す。
        """
        cw.cwpy.set_pcards()
        cw.util.remove(cw.util.join_paths(cw.tempdir, u"ScenarioLog"))
        path = cw.util.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"
        path = cw.util.get_yadofilepath(path)

        if path:
            cw.util.decompress_zip(path, cw.tempdir, "ScenarioLog")
            musicpaths = self.load_log(cw.util.join_paths(cw.tempdir, u"ScenarioLog/ScenarioLog.xml"), False)
            return True, musicpaths
        else:
            self.create_log()
            return False, None

    def remove_log(self, debuglog):
        if debuglog:
            dpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Members")
            for pcard in cw.cwpy.get_pcards():
                fname = os.path.basename(pcard.data.fpath)
                fpath = cw.util.join_paths(dpath, fname)
                prop = cw.header.GetProperty(fpath)
                old_coupons = set()
                get_coupons = []
                lose_coupons = []

                for _coupon, attrs, name in prop.third.get("Coupons", []):
                    old_coupons.add(name)
                    value = int(attrs.get("value", "0"))
                    if not pcard.has_coupon(name):
                        lose_coupons.append((name, value))
                for name in pcard.get_coupons():
                    if not name in old_coupons:
                        value = pcard.get_couponvalue(name)
                        get_coupons.append((name, value))
                debuglog.add_player(pcard, get_coupons, lose_coupons)

            dpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party")
            for fname in os.listdir(dpath):
                if fname.lower().endswith(".xml"):
                    prop = cw.header.GetProperty(cw.util.join_paths(dpath, fname))
                    money = int(prop.properties.get("Money", str(cw.cwpy.ydata.party.money)))
                    debuglog.set_money(money, cw.cwpy.ydata.party.money)
                    break

            data = xml2etree(cw.util.join_paths(cw.tempdir, u"ScenarioLog/ScenarioLog.xml"))

            for gossip, get in cw.util.sorted_by_attr(self.gossips.iteritems()):
                debuglog.add_gossip(gossip, get)

            for compstamp, get in cw.util.sorted_by_attr(self.compstamps.iteritems()):
                debuglog.add_compstamp(compstamp, get)

            for type in ("SkillCard", "ItemCard", "BeastCard"):
                dname = "Deleted" + type
                dpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party", dname)
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
                            if type <> "BeastCard" or attachment:
                                debuglog.add_lostcard(type, name, desc, scenario, author, premium)

        cw.util.remove(cw.util.join_paths(cw.tempdir, u"ScenarioLog"))
        path = cw.util.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"
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

        return "", False

    def get_resdata(self, isbattle, resid):
        if isbattle:
            data = self.get_battledata(resid)
        else:
            data = self.get_areadata(resid)

        if data is None:
            return None

        return xml2etree(element=data)

    def get_carddata(self, linkdata, inusecard=True):
        return linkdata

    def is_updatedfilenames(self):
        """WSNシナリオのデータ(XML)のファイル名がデータテーブル
        作成時点から変更されている場合はTrueを返す。
        """
        return False

    def _get_resdata(self, table, resid, tag, nocache, resname=u"?", rootattrs=None):
        fpath0 = table.get(resid, (u"", u"(未定義の%s ID:%s)" % (resname, resid)))[1]
        fpath = self._get_resfpath(table, resid)
        if fpath is None:
            # イベント中に存在しないリソースを読み込もうとする
            # クラシックシナリオがいくつか確認されているため、
            # 読込失敗の警告ダイアログは出さないようにする。
            ##s = u"%s の読込に失敗しました。" % (os.path.basename(fpath0))
            ##cw.cwpy.call_modaldlg("ERROR", text=s)
            return None
        try:
            return xml2element(fpath, tag, nocache=nocache, rootattrs=rootattrs)
        except:
            cw.util.print_ex()
            s = u"%s の読込に失敗しました。" % (os.path.basename(fpath0))
            cw.cwpy.call_modaldlg("ERROR", text=s)
            return None

    def _get_resname(self, table, resid):
        return table.get(resid, (None, None))[0]

    def _get_resfpath(self, table, resid):
        fpath = table.get(resid, None)
        if fpath is None:
            return None
        if not os.path.isfile(fpath[1]) and self.is_updatedfilenames():
            self._init_xmlpaths(xmlonly=True)
            fpath = table.get(resid, None)
            if fpath is None:
                return None
        return fpath[1]

    def _get_resids(self, table):
        return table.keys()

    def get_areadata(self, resid, tag="", nocache=False, rootattrs=None):
        return self._get_resdata(self._areas, resid, tag, nocache, resname=u"エリア", rootattrs=rootattrs)

    def get_areaname(self, resid):
        return self._get_resname(self._areas, resid)

    def get_areafpath(self, resid):
        return self._get_resfpath(self._areas, resid)

    def get_areaids(self):
        return self._get_resids(self._areas)

    def get_battledata(self, resid, tag="", nocache=False, rootattrs=None):
        return self._get_resdata(self._battles, resid, tag, nocache, resname=u"バトル", rootattrs=rootattrs)

    def get_battlename(self, resid):
        return self._get_resname(self._battles, resid)

    def get_battlefpath(self, resid):
        return self._get_resfpath(self._battles, resid)

    def get_battleids(self):
        return self._get_resids(self._battles)

    def get_packagedata(self, resid, tag="", nocache=False, rootattrs=None):
        return self._get_resdata(self._packs, resid, tag, nocache, resname=u"パッケージ", rootattrs=rootattrs)

    def get_packagename(self, resid):
        return self._get_resname(self._packs, resid)

    def get_packagefpath(self, resid):
        return self._get_resfpath(self._packs, resid)

    def get_packageids(self):
        return self._get_resids(self._packs)

    def get_castdata(self, resid, tag="", nocache=False, rootattrs=None):
        return self._get_resdata(self._casts, resid, tag, nocache, resname=u"キャスト", rootattrs=rootattrs)

    def get_castname(self, resid):
        return self._get_resname(self._casts, resid)

    def get_castfpath(self, resid):
        return self._get_resfpath(self._casts, resid)

    def get_castids(self):
        return self._get_resids(self._casts)

    def get_skilldata(self, resid, tag="", nocache=False, rootattrs=None):
        return self._get_resdata(self._skills, resid, tag, nocache, resname=u"特殊技能", rootattrs=rootattrs)

    def get_skillname(self, resid):
        return self._get_resname(self._skills, resid)

    def get_skillfpath(self, resid):
        return self._get_resfpath(self._skills, resid)

    def get_skillids(self):
        return self._get_resids(self._skills)

    def get_itemdata(self, resid, tag="", nocache=False, rootattrs=None):
        return self._get_resdata(self._items, resid, tag, nocache, resname=u"アイテム", rootattrs=rootattrs)

    def get_itemname(self, resid):
        return self._get_resname(self._items, resid)

    def get_itemfpath(self, resid):
        return self._get_resfpath(self._items, resid)

    def get_itemids(self):
        return self._get_resids(self._items)

    def get_beastdata(self, resid, tag="", nocache=False, rootattrs=None):
        return self._get_resdata(self._beasts, resid, tag, nocache, resname=u"召喚獣", rootattrs=rootattrs)

    def get_beastname(self, resid):
        return self._get_resname(self._beasts, resid)

    def get_beastfpath(self, resid):
        return self._get_resfpath(self._beasts, resid)

    def get_beastids(self):
        return self._get_resids(self._beasts)

    def get_infodata(self, resid, tag="", nocache=False, rootattrs=None):
        return self._get_resdata(self._infos, resid, tag, nocache, resname=u"情報", rootattrs=rootattrs)

    def get_infoname(self, resid):
        return self._get_resname(self._infos, resid)

    def get_infofpath(self, resid):
        return self._get_resfpath(self._infos, resid)

    def get_infoids(self):
        return self._get_resids(self._infos)

    def _get_carddatapath(self, type, resid, dpath):
        dpath = cw.util.join_paths(dpath, type)
        if not os.path.isdir(dpath):
            return ""
        for fpath in os.listdir(dpath):
            if not fpath.lower().endswith(".xml"):
                continue
            fpath = cw.util.join_paths(dpath, fpath)
            idstr = cw.header.GetName(fpath, tagname="Id").name
            if not idstr or int(idstr) <> resid:
                continue
            return fpath

        return ""

    def copy_carddata(self, linkdata, dstdir, from_scenario, scedir, imgpaths):
        """参照で指定された召喚獣カードを宿へコピーする。"""
        assert linkdata.tag == "BeastCard"
        resid = linkdata.getint("Property/LinkId", 0)
        if resid == 0:
            return

        if scedir == self.scedir:
            path = self.get_beastfpath(resid)
            if not path or not os.path.isfile(path):
                return
            data = self.get_beastdata(resid)
            if data is None:
                return
            data = xml2etree(element=data)
            dstpath = cw.util.relpath(path, self.tempdir)
        else:
            path = self._get_carddatapath(linkdata.tag, resid, scedir)
            try:
                data = xml2etree(path)
            except:
                cw.util.print_ex()
                return
            dstpath = cw.util.relpath(path, scedir)

        if path in imgpaths:
            return

        data = copy.deepcopy(data)

        dstpath = cw.util.join_paths(dstdir, dstpath)
        imgpaths[path] = dstpath
        can_loaded_scaledimage = data.getbool(".", "scaledimage", False)

        cw.cwpy.copy_materials(data, dstdir, from_scenario=from_scenario, scedir=scedir, imgpaths=imgpaths,
                               can_loaded_scaledimage=can_loaded_scaledimage)
        data.fpath = dstpath
        data.write_xml(True)

    def change_data(self, resid, data=None):
        if data is None:
            data = self.get_resdata(cw.cwpy.is_battlestatus(), resid)
        if data is None:
            return False
        self.data = data

        if isinstance(self, ScenarioData):
            self.set_versionhint(cw.HINT_AREA, cw.cwpy.sct.from_basehint(self.data.getattr("Property", "versionHint", "")))
        cw.cwpy.event.refresh_areaname()
        self.events = cw.event.EventEngine(self.data.getfind("Events"))
        # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
        self.playerevents = cw.event.EventEngine(self.data.getfind("PlayerCardEvents/Events", False))
        return True

    def start_event(self, keynum=None, keycodes=[][:]):
        cw.cwpy.statusbar.change(False)
        self.events.start(keynum=keynum, keycodes=keycodes)
        if not cw.cwpy.is_dealing() and not cw.cwpy.battle:
            cw.cwpy.statusbar.change()
            if not (pygame.event.peek(pygame.locals.USEREVENT)):
                cw.cwpy.show_party()
                cw.cwpy.disposition_pcards()
                cw.cwpy.draw()

    def get_currentareaname(self):
        """現在滞在中のエリアの名前を返す"""
        if cw.cwpy.is_battlestatus():
            name = self.get_battlename(cw.cwpy.areaid)
        else:
            name = self.get_areaname(cw.cwpy.areaid)
        if name is None:
            name = u"(読込失敗)"
        return name

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

    def get_mcarddata(self, resid=None, battlestatus=None, data=None):
        """spreadtypeの値("Custom", "Auto")と
        メニューカードのElementのリストをタプルで返す。
        id: 取得対象のエリア。不指定の場合は現在のエリア。
        """
        if not isinstance(battlestatus, bool):
            battlestatus = cw.cwpy.is_battlestatus()

        if data is None:
            if resid is None:
                data = self.data
            elif battlestatus:
                data = self.get_battledata(resid)
                if data is None:
                    return ("Custom", [])
                data = xml2etree(element=data)
            else:
                data = self.get_areadata(resid)
                if data is None:
                    return ("Custom", [])
                data = xml2etree(element=data)

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

    def get_bgmpaths(self):
        """現在使用可能なBGMのパスのリストを返す。"""
        seq = []
        dpaths = [cw.util.join_paths(cw.cwpy.skindir, u"Bgm"), cw.util.join_paths(cw.cwpy.skindir, u"BgmAndSound")]
        for dpath2 in os.listdir(u"Data/Materials"):
            dpath2 = cw.util.join_paths(u"Data/Materials", dpath2)
            if os.path.isdir(dpath2):
                dpath3 = cw.util.join_paths(dpath2, u"Bgm")
                if os.path.isdir(dpath3):
                    dpaths.append(dpath3)
                dpath3 = cw.util.join_paths(dpath2, u"BgmAndSound")
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

    def fullrecovery_fcards(self):
        """同行中のNPCの状態を初期化する。"""
        pass # stub

    def has_infocards(self):
        """情報カードを1枚でも所持しているか。"""
        return any(self.infocards)

    def _tidying_infocards(self):
        """情報カードの情報を整理する。"""
        nums = filter(lambda a: 0 < a, self.infocards)
        indexes = {}
        for i, num in enumerate(sorted(nums)):
            indexes[num] = i + 1
        self.infocard_maxindex = len(nums)
        for i, num in enumerate(self.infocards):
            self.infocards[i] = indexes[num]

    def get_infocards(self, order):
        """情報カードのID一覧を返す。
        orderがTrueの場合は入手の逆順に返す。
        """
        infotable = []
        for resid, num in enumerate(self.infocards):
            if 0 < num:
                if order:
                    infotable.append((num, resid))
                else:
                    infotable.append(resid)
        if not order:
            return infotable

        return map(lambda a: a[1], reversed(sorted(infotable)))

    def append_infocard(self, resid):
        """情報カードを追加する。"""
        if 0x7fffffff <= self.infocard_maxindex:
            self._tidying_infocards()
        if len(self.infocards) <= resid:
            self.infocards.extend([0] * (resid-len(self.infocards)+1))
        self.infocard_maxindex += 1
        self.infocards[resid] = self.infocard_maxindex

    def remove_infocard(self, resid):
        """情報カードを除去する。"""
        if resid < len(self.infocards):
            self.infocards[resid] = 0

    def has_infocard(self, resid):
        """情報カードを所持しているか。"""
        return resid < len(self.infocards) and self.infocards[resid]

    def count_infocards(self):
        """情報カードの所持枚数を返す。"""
        return len(self.infocards) - self.infocards.count(0)

    def get_infocardheaders(self):
        """所持する情報カードのInfoCardHeaderを入手の逆順で返す。"""
        headers = []
        for resid in self.get_infocards(order=True):
            if resid in self._infocard_cache:
                header = self._infocard_cache[resid]
                headers.append(header)
            elif resid in self.get_infoids():
                rootattrs = {}
                e = self.get_infodata(resid, "Property", rootattrs=rootattrs)
                if e is None:
                    continue
                header = cw.header.InfoCardHeader(e, cw.util.str2bool(rootattrs.get("scaledimage", "False")))
                self._infocard_cache[resid] = header
                headers.append(header)
        return headers


#-------------------------------------------------------------------------------
#　シナリオデータ
#-------------------------------------------------------------------------------

class ScenarioData(SystemData):

    def __init__(self, header, cardonly=False):
        self.data = None
        self.is_playing = True
        self.in_f9 = False
        self.in_endprocess = False
        self.background_image_mtime = {}
        self.fpath = cw.util.get_linktarget(header.get_fpath())
        self.mtime = os.path.getmtime(self.fpath)
        self.name = header.name
        self.author = header.author
        self.startid = header.startid
        self.can_loaded_scaledimage = True
        if not cardonly:
            cw.cwpy.areaid = self.startid
        if os.path.isfile(self.fpath):
            # zip解凍・解凍したディレクトリを登録
            self.tempdir = cw.cwpy.ydata.recenthistory.check(self.fpath)

            if self.tempdir:
                cw.cwpy.ydata.recenthistory.moveend(self.fpath)
                self._find_summaryintemp()
            else:
                self.tempdir = cw.util.join_paths(cw.tempdir, u"Scenario")
                orig_tempdir = self._decompress(False)
                cw.cwpy.ydata.recenthistory.append(self.fpath, orig_tempdir)
        else:
            # 展開済みシナリオ
            self.tempdir = self.fpath

        if cw.scenariodb.TYPE_CLASSIC == header.type:
            cw.cwpy.classicdata = cw.binary.cwscenario.CWScenario(
                self.tempdir, cw.util.join_paths(cw.tempdir, u"OldScenario"), cw.cwpy.setting.skintype,
                materialdir="", image_export=False)

        # 特殊文字の画像パスの集合(正規表現)
        self._r_specialchar = re.compile(r"^font_(.)[.]bmp$")

        self._areas = {}
        self._battles = {}
        self._packs = {}
        self._casts = {}
        self._infos = {}
        self._items = {}
        self._skills = {}
        self._beasts = {}

        # 各種xmlファイルのパスを設定
        self._init_xmlpaths()

        if cardonly:
            return

        # 特殊エリアのメニューカードを作成
        self._init_sparea_mcards()
        # エリアデータ初期化
        self.data = None
        self.events = None
        # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
        self.playerevents = None
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
        # 情報カードのリスト
        # 情報カードの枚数分の配列を確保し、各位置に入手順序を格納する
        self.infocards = []
        # 最後に設定した情報カードの入手順
        self.infocard_maxindex = 0
        # InfoCardHeaderのキャッシュ
        self._infocard_cache = {}
        # 情報カードを手に入れてから
        # 情報カードビューを開くまでの間True
        self.notice_infoview = False
        self.infocards_beforeevent = None # イベント開始前の所持情報カードのset
        # 戦闘エリア移動前のエリアデータ(ID, MusicFullPath, BattleMusicPath)
        self.pre_battleareadata = None
        # バトル中、自動で行動開始するか
        self.autostart_round = False
        # flag set
        self._init_flags()
        # step set
        self._init_steps()
        # refresh debugger
        self._init_debugger()

        # ロードしたデータファイルのキャッシュ
        self.data_cache = {}
        # ロードしたイメージ等のリソースのキャッシュ
        self.resource_cache = {}
        self.resource_cache_size = 0
        # メッセージのバックログ
        self.backlog = []
        # キャンプ中に移動したカードの使用回数の記憶
        self.uselimit_table = {}

        # イベントが任意箇所に到達した時に実行を停止するためのブレークポイント
        self.breakpoints = cw.cwpy.breakpoint_table.get((self.name, self.author), set())

        # 各段階の互換性マーク
        self.versionhint = [
            None, # メッセージ表示時の話者(キャストまたはカード)
            None, # 使用中のカード
            None, # エリア・バトル・パッケージ
            None, # シナリオ本体
        ]

        if cw.cwpy.classicdata:
            self.versionhint[cw.HINT_SCENARIO] = cw.cwpy.classicdata.versionhint

        self.ignorecase_table = {}
        # FIXME: 大文字・小文字を区別しないシステムでリソース内のファイルの
        #        取得に失敗する事があるので、すべて小文字のパスをキーにして
        #        真のファイル名へのマッピングをしておく。
        #        主にこの問題は手書きされる'*.jpy1'内で発生する。
        for dpath, _dnames, fnames in os.walk(self.tempdir):
            for fname in fnames:
                path = cw.util.join_paths(dpath, fname)
                if os.path.isfile(path):
                    self.ignorecase_table[path.lower()] = path

    def check_archiveupdated(self, reload):
        """シナリオが圧縮されており、
        前回の展開より後に更新されていた場合は
        更新分をアーカイブから再取得する。
        """
        if not os.path.isfile(self.fpath):
            return

        mtime = os.path.getmtime(self.fpath)
        if self.mtime <> mtime:
            self._decompress(True)
            self.mtime = mtime
            if reload:
                self._reload()

    def _decompress(self, overwrite):
        if self.fpath.lower().endswith(".cab"):
            decompress = cw.util.decompress_cab
        else:
            decompress = cw.util.decompress_zip

        # 展開を別スレッドで実行し、進捗をステータスバーに表示
        self._progress = False
        self._arcname = os.path.basename(self.fpath)
        self._format = u""
        self._cancel_decompress = False
        def startup(filenum):
            def func():
                self._filenum = filenum
                self._format = u"%%sを展開中... (%%%ds/%%s)" % len(str(self._filenum))
                cw.cwpy.expanding = self._format % (self._arcname, 0, self._filenum)
                cw.cwpy.expanding_max = self._filenum
                cw.cwpy.expanding_min = 0
                cw.cwpy.expanding_cur = 0
                cw.cwpy.statusbar.change()
            cw.cwpy.exec_func(func)
        def progress(cur):
            if not cw.cwpy.is_runningstatus() or self._cancel_decompress:
                return True # cancel
            def func():
                if not cw.cwpy.expanding:
                    return
                cw.cwpy.expanding_cur = cur
                cw.cwpy.expanding = self._format % (self._arcname, cur, self._filenum)
                cw.cwpy.sbargrp.update(cw.cwpy.scr_draw)
                cw.cwpy.draw()
                self._progress = False
            if not self._progress or cur == cw.cwpy.expanding_max:
                self._progress = True
                cw.cwpy.exec_func(func)
            return False

        self._error = None
        def run_decompress():
            try:
                self.tempdir = decompress(self.fpath, self.tempdir,
                                          startup=startup, progress=progress,
                                          overwrite=overwrite)
            except Exception, e:
                cw.util.print_ex(file=sys.stderr)
                self._error = e

        cw.cwpy.is_decompressing = True

        try:
            thr = threading.Thread(target=run_decompress)
            thr.start()
            while thr.is_alive():
                cw.cwpy.eventhandler.run()
                cw.cwpy.tick_clock()
                cw.cwpy.input()
            cw.cwpy.eventhandler.run()
        except cw.event.EffectBreakError, ex:
            self._cancel_decompress = True
            thr.join()
            raise ex
        finally:
            cw.cwpy.is_decompressing = False
            if not cw.cwpy.is_runningstatus():
                raise cw.event.EffectBreakError()
            cw.cwpy.expanding = u""
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

    def _find_summaryintemp(self):
        # 展開先のフォルダのサブフォルダ内にシナリオ本体がある場合、
        # self.tempdirをサブフォルダに設定する
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
                    fnames = map(lambda f: f.lower(), fnames)
                    if "summary.wsm" in fnames or "summary.xml" in fnames:
                        # アーカイヴのサブフォルダにシナリオがある
                        self.tempdir = dpath
                        break
            self.tempdir = cw.util.join_paths(self.tempdir)

    def get_versionhint(self, frompos=0):
        """現在有効になっている互換性マークを返す。"""
        for i, hint in enumerate(self.versionhint[frompos:]):
            if cw.HINT_AREA <= i + frompos and cw.cwpy.event.in_inusecardevent:
                # 使用時イベント中であればエリア・シナリオの互換性情報は見ない
                break
            if hint:
                return hint
        return None

    def set_versionhint(self, pos, hint):
        """互換性モードを設定する。"""
        last = self.get_versionhint()
        self.versionhint[pos] = hint
        if cw.HINT_AREA <= pos and cw.cwpy.sct.to_basehint(last) <> cw.cwpy.sct.to_basehint(self.get_versionhint()):
            cw.cwpy.update_titlebar()

    def get_carddata(self, linkdata, inusecard=True):
        """参照で設定されているデータの実体を取得する。"""
        resid = linkdata.getint("Property/LinkId", 0)
        if resid == 0:
            return linkdata

        if inusecard:
            inusecard = cw.cwpy.event.get_inusecard()
        if inusecard and (cw.cwpy.event.in_inusecardevent or cw.cwpy.event.in_cardeffectmotion) and (not inusecard.scenariocard or inusecard.carddata.gettext("Property/Materials", "")):
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
                data = self.get_skilldata(resid, nocache=True)
            elif linkdata.tag == "ItemCard":
                data = self.get_itemdata(resid, nocache=True)
            elif linkdata.tag == "BeastCard":
                data = self.get_beastdata(resid, nocache=True)
            else:
                assert False
            if data is None:
                return None

        prop1 = linkdata.find("Property")
        ule1 = linkdata.find("Property/UseLimit")
        he1 = linkdata.find("Property/Hold")

        prop2 = data.find("Property")
        ule2 = data.find("Property/UseLimit")
        he2 = data.find("Property/Hold")

        if not ule1 is None and not ule2 is None:
            prop2.remove(ule2)
            prop2.append(ule1)
        if not he1 is None and not he2 is None:
            prop2.remove(he2)
            prop2.append(he1)
        return data

    def save_breakpoints(self):
        key = (self.name, self.author)
        if self.breakpoints:
            cw.cwpy.breakpoint_table[key] = self.breakpoints
        elif key in cw.cwpy.breakpoint_table:
            del cw.cwpy.breakpoint_table[key]

    def change_data(self, resid, data=None):
        if data is None:
            self.check_archiveupdated(True)
        return SystemData.change_data(self, resid, data=data)

    def reload(self):
        self.check_archiveupdated(False)
        self._reload()

    def _reload(self):
        flagvals = {}
        stepvals = {}
        for name, flag in self.flags.items():
            flagvals[name] = flag.value
        for name, step in self.steps.items():
            stepvals[name] = step.value
        self.data_cache = {}
        self.resource_cache = {}
        self.resource_cache_size = 0
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
        def func():
            cw.cwpy.is_debuggerprocessing = False
            if cw.cwpy.is_showingdebugger() and cw.cwpy.event:
                cw.cwpy.event.refresh_tools()
        cw.cwpy.frame.exec_func(func)

    def is_updatedfilenames(self):
        """WSNシナリオのデータ(XML)のファイル名がデータテーブル
        作成時点から変更されている場合はTrueを返す。
        """
        datafilenames = set()

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
                if not path in self._datafilenames:
                    return True
                datafilenames.add(path)

        return datafilenames <> self._datafilenames

    def _init_xmlpaths(self, xmlonly=False):
        """
        シナリオで使用されるXMLファイルのパスを辞書登録。
        また、"Summary.xml"のあるフォルダをシナリオディレクトリに設定する。
        """
        if not xmlonly:
            # 解凍したシナリオのディレクトリ
            self.scedir = ""
            # summary(CWPyElementTree)
            self.summary = None

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

        for dpath, _dnames, fnames in os.walk(self.tempdir):
            isdatadir = os.path.basename(dpath).lower() in _WSN_DATA_DIRS
            if xmlonly and not isdatadir:
                continue
            for fname in fnames:
                lf = fname.lower()

                if xmlonly and not lf.endswith(".xml"):
                    continue

                # "font_*.*"のファイルパスの画像を特殊文字に指定
                if self.eat_spchar(dpath, fname, self.can_loaded_scaledimage):
                    continue
                else:
                    if not (lf.endswith(".xml") or lf.endswith(".wsm") or lf.endswith(".wid")):
                        # シナリオファイル以外はここで処理終わり
                        continue
                    if (lf.endswith(".wsm") or lf.endswith(".wid")) and dpath <> self.tempdir:
                        # クラシックなシナリオはディレクトリ直下のみ読み込む
                        continue

                path = cw.util.join_paths(dpath, fname)
                if not os.path.isfile(path):
                    continue
                if lf.endswith(".xml"):
                    self._datafilenames.add(os.path.normcase(path))

                if (lf == "summary.xml" or lf == "summary.wsm") and not self.summary:
                    self.scedir = dpath.replace("\\", "/")
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
                    # クラシックなシナリオの基本要素一覧情報
                    wdata, _filedata = cw.cwpy.classicdata.load_file(path, nameonly=True)
                    if wdata is None:
                        continue
                    resid = wdata.id
                    name = wdata.name

                ldpath = dpath.lower()
                if ldpath.endswith("area") or lf.startswith("area"):
                    self._areas[resid] = (name, path)
                elif ldpath.endswith("battle") or lf.startswith("battle"):
                    self._battles[resid] = (name, path)
                elif ldpath.endswith("package") or lf.startswith("package"):
                    self._packs[resid] = (name, path)
                elif ldpath.endswith("castcard") or lf.startswith("mate"):
                    self._casts[resid] = (name, path)
                elif ldpath.endswith("infocard") or lf.startswith("info"):
                    self._infos[resid] = (name, path)
                elif ldpath.endswith("itemcard") or lf.startswith("item"):
                    self._items[resid] = (name, path)
                elif ldpath.endswith("skillcard") or lf.startswith("skill"):
                    self._skills[resid] = (name, path)
                elif ldpath.endswith("beastcard") or lf.startswith("beast"):
                    self._beasts[resid] = (name, path)

        if not xmlonly and not self.summary:
            raise ValueError("Summary file is not found.")

        # 特殊エリアのxmlファイルのパスを設定
        dpath = cw.util.join_paths(cw.cwpy.skindir, u"Resource/Xml/Scenario")

        for fname in os.listdir(dpath):
            path = cw.util.join_paths(dpath, fname)

            if os.path.isfile(path) and fname.endswith(".xml"):
                e = xml2element(path, "Property")
                resid = e.getint("Id")
                name = e.gettext("Name")
                self._areas[resid] = (name, path)

        # WSNバージョン
        self.wsn_version = self.summary.getattr(".", "dataVersion", "")

    def update_scale(self):
        # 特殊文字の画像パスの集合(正規表現)
        SystemData.update_scale(self)

        for dpath, _dnames, fnames in os.walk(self.tempdir):
            for fname in fnames:
                if os.path.isfile(cw.util.join_paths(dpath, fname)):
                    self.eat_spchar(dpath, fname, self.can_loaded_scaledimage)

    def eat_spchar(self, dpath, fname, can_loaded_scaledimage):
        # "font_*.*"のファイルパスの画像を特殊文字に指定
        if self._r_specialchar.match(fname.lower()):
            def load(dpath, fname):
                path = cw.util.get_materialpath(fname, cw.M_IMG, scedir=dpath, findskin=False)
                image = cw.util.load_image(path, True, can_loaded_scaledimage=can_loaded_scaledimage)
                return image, True
            m = self._r_specialchar.match(fname.lower())
            name = "#%s" % (m.group(1))
            cw.cwpy.rsrc.specialchars.set(name, load, dpath, fname)
            cw.cwpy.rsrc.specialchars_is_changed = True
            return True

        else:
            return False

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
            spchars = e.getbool(".", "spchars", False)
            self.flags[name] = Flag(value, name, truename, falsename, defaultvalue=value,
                                    spchars=spchars)

    def _init_steps(self):
        """
        summary.xmlで定義されているステップを初期化。
        """
        self.steps = {}

        for e in self.summary.getfind("Steps"):
            value = e.getint(".", "default")
            name = e.gettext("Name", "")
            valuenames = []
            for ev in e:
                if ev.tag.startswith("Value"):
                    valuenames.append(ev.text if ev.text else u"")
            spchars = e.getbool(".", "spchars", False)
            self.steps[name] = Step(value, name, valuenames, defaultvalue=value,
                                    spchars=spchars)

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
        self.is_playing = True

        for header in cw.cwpy.ydata.party.get_allcardheaders():
            header.set_scenariostart()

    def end(self, showdebuglog=False):
        """
        シナリオの正規終了時の共通処理をまとめたもの。
        冒険の中断時やF9時には呼ばない。
        """
        putdebuglog = showdebuglog and cw.cwpy.is_debugmode() and cw.cwpy.setting.show_debuglogdialog
        debuglog = None
        if putdebuglog:
            debuglog = cw.debug.logging.DebugLog()

        if debuglog:
            for fcard in cw.cwpy.get_fcards():
                debuglog.add_friend(fcard)

        # NPCの連れ込み
        cw.cwpy.ydata.join_npcs()

        self.is_playing = False

        cw.cwpy.ydata.party.set_lastscenario([], u"")

        # ロストした冒険者を削除
        for path in self.lostadventurers:
            if not path.lower().startswith("yado"):
                path = cw.util.join_yadodir(path)
            ccard = cw.character.Character(yadoxml2etree(path))
            ccard.remove_numbercoupon()
            if debuglog:
                debuglog.add_lostplayer(ccard)

            # "＿消滅予約"を持ってない場合、アルバムに残す
            if not ccard.has_coupon(u"＿消滅予約"):
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
                    debuglog.add_gotcard(header.type, header.name, header.desc, header.scenario, header.author, header.premium)
                header.set_scenarioend()

            # 移動済みの荷物袋カードを削除
            for header in cw.cwpy.ydata.party.backpack_moved:
                if header.moved == 2:
                    # 素材も含めて完全削除
                    if debuglog and not header.scenariocard:
                        debuglog.add_lostcard(header.type, header.name, header.desc, header.scenario, header.author, header.premium)
                    cw.cwpy.remove_xml(header)
                else:
                    # どこかで所有しているので素材は消さない
                    cw.cwpy.ydata.deletedpaths.add(header.fpath)
            cw.cwpy.ydata.party.backpack_moved = []

        # 保存済みJPDCイメージを宿フォルダへ移動
        cw.header.SavedJPDCImageHeader.create_header(debuglog)

        cw.cwpy.ydata.party.remove_numbercoupon()
        self.remove_log(debuglog)
        cw.cwpy.ydata.deletedpaths.update(self.deletedpaths)

        if debuglog:
            def func(sname, debuglog):
                dlg = cw.debug.logging.DebugLogDialog(cw.cwpy.frame, sname, debuglog)
                cw.cwpy.frame.move_dlg(dlg)
                dlg.ShowModal()
                dlg.Destroy()
            cw.cwpy.frame.exec_func(func, self.name, debuglog)

    def f9(self):
        """
        シナリオ強制終了。俗に言うファッ○ユー。
        """
        self.in_f9 = True
        cw.cwpy.exec_func(cw.cwpy.f9)

    def create_log(self):
        # play log
        cw.cwpy.advlog.start_scenario()

        # log
        cw.xmlcreater.create_scenariolog(self, cw.util.join_paths(cw.tempdir, u"ScenarioLog/ScenarioLog.xml"), False,
                                         cw.cwpy.advlog.logfilepath)
        # Party and members xml update
        cw.cwpy.ydata.party.write()
        # party
        os.makedirs(cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party"))
        path = cw.util.get_yadofilepath(cw.cwpy.ydata.party.data.fpath)
        dstpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party",
                                                    os.path.basename(path))
        shutil.copy2(path, dstpath)
        # member
        os.makedirs(cw.util.join_paths(cw.tempdir, u"ScenarioLog/Members"))

        for data in cw.cwpy.ydata.party.members:
            path = cw.util.get_yadofilepath(data.fpath)
            dstpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Members",
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
        path = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Backpack.xml")
        etree = cw.data.xml2etree(element=element)
        etree.write(path)

        # JPDCイメージ
        dpath1 = cw.util.join_paths(cw.tempdir, u"ScenarioLog/TempFile")
        key = (self.name, self.author)
        header = cw.cwpy.ydata.savedjpdcimage.get(key, None)
        if header:
            dpath2 = cw.util.join_paths(cw.cwpy.tempdir, u"SavedJPDCImage", header.dpath)
            for fpath in header.fpaths:
                frompath = cw.util.join_paths(dpath2, u"Materials", fpath)
                frompath = cw.util.get_yadofilepath(frompath)
                if not frompath:
                    continue
                topath = cw.util.join_paths(dpath1, fpath)
                dpath3 = os.path.dirname(topath)
                if not os.path.isdir(dpath3):
                    os.makedirs(dpath3)
                shutil.copy2(frompath, topath)

        # create_zip
        path = cw.util.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"

        if path.startswith(cw.cwpy.yadodir):
            path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)

        cw.util.compress_zip(cw.util.join_paths(cw.tempdir, u"ScenarioLog"), path, unicodefilename=True)
        cw.cwpy.ydata.deletedpaths.discard(path)

    def load_log(self, path, recording):
        etree = xml2etree(path)
        ##if not recording:
        ##    cw.cwpy.debug = etree.getbool("Property/Debug")

        ##    if not cw.cwpy.debug == cw.cwpy.setting.debug:
        ##        cw.cwpy.statusbar.change()

        ##        if not cw.cwpy.debug and cw.cwpy.is_showingdebugger():
        ##            cw.cwpy.frame.exec_func(cw.cwpy.frame.close_debugger)
        self.autostart_round = etree.getbool("Property/RoundAutoStart", False)
        self.notice_infoview = etree.getbool("Property/NoticeInfoView", False)
        cw.cwpy.statusbar.loading = True

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
        self.infocard_maxindex = 0
        for e in reversed(etree.getfind("InfoCards")):
            resid = int(e.text)
            if resid in self.get_infoids():
                self.append_infocard(resid)

        self.friendcards = []
        for e in etree.getfind("CastCards"):
            if e.tag == "FriendCard":
                # IDのみ。変換直後の宿でこの状態になる
                e = self.get_castdata(int(e.text), nocache=True)
                if not e is None:
                    fcard = cw.sprite.card.FriendCard(data=e)
                    self.friendcards.append(fcard)
            else:
                fcard = cw.sprite.card.FriendCard(data=e)
                self.friendcards.append(fcard)

        if not recording:
            for e in etree.getfind("DeletedFiles"):
                self.deletedpaths.add(e.text)

            for e in etree.getfind("LostAdventurers"):
                self.lostadventurers.add(e.text)

        e = etree.getfind("BgImages")
        elements = cw.cwpy.sdata.get_bgdata(e)
        ttype = ("Default", "Default")
        cw.cwpy.background.load(elements, False, ttype, bginhrt=False, nocheckvisible=True)
        self.startid = cw.cwpy.areaid = etree.getint("Property/AreaId")

        logfilepath = etree.gettext("Property/LogFile", u"")
        cw.cwpy.advlog.resume_scenario(logfilepath)

        musicpaths = []
        for music in cw.cwpy.music:
            musicpaths.append((music.path, music.subvolume, music.loopcount, music.inusecard))

        e_mpaths = etree.find("Property/MusicPaths")
        if not e_mpaths is None:
            for i, e in enumerate(e_mpaths):
                channel = e.getint(".", "channel", i)
                path = e.text if e.text else ""
                subvolume = e.getint(".", "volume", 100)
                loopcount = e.getint(".", "loopcount", 0)
                inusecard = e.getbool(".", "inusecard", False)
                if 0 <= channel and channel < len(musicpaths):
                    musicpaths[channel] = (path, subvolume, loopcount, inusecard)
        else:
            # BGMが1CHのみだった頃の互換性維持
            e = etree.find("Property/MusicPath")
            if not e is None:
                channel = e.getint(".", "channel", 0)
                path = e.text if e.text else ""
                subvolume = e.getint(".", "volume", 100)
                loopcount = e.getint(".", "loopcount", 0)
                inusecard = e.getbool(".", "inusecard", False)
                if 0 <= channel and channel < len(musicpaths):
                    musicpaths[channel] = (path, subvolume, loopcount, inusecard)
        return musicpaths

    def update_log(self):
        cw.xmlcreater.create_scenariolog(self, cw.util.join_paths(cw.tempdir, u"ScenarioLog/ScenarioLog.xml"), False,
                                         cw.cwpy.advlog.logfilepath)
        cw.cwpy.advlog.end_scenario(False, False)

        path = cw.util.splitext(cw.cwpy.ydata.party.data.fpath)[0] + ".wsl"

        if path.startswith("Yado"):
            path = path.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)

        cw.util.compress_zip(cw.util.join_paths(cw.tempdir, u"ScenarioLog"), path, unicodefilename=True)

    def get_bgmpaths(self):
        """現在使用可能なBGMのパスのリストを返す。"""
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

    def fullrecovery_fcards(self):
        """同行中のNPCを回復する。"""
        seq = []
        for fcard in self.friendcards:
            self.set_versionhint(cw.HINT_MESSAGE, fcard.versionhint)
            # 互換動作: 1.28以前は戦闘毎に同行キャストの状態が完全に復元される
            if cw.cwpy.sct.lessthan("1.28", self.get_versionhint(cw.HINT_MESSAGE)):
                e = cw.cwpy.sdata.get_castdata(fcard.id, nocache=True)
                if not e is None:
                    fcard = cw.sprite.card.FriendCard(data=e)
            else:
                fcard.set_fullrecovery()
                fcard.update_image()
            seq.append(fcard)
            self.set_versionhint(cw.HINT_MESSAGE, None)
        self.friendcards = seq

class Flag(object):
    def __init__(self, value, name, truename, falsename, defaultvalue, spchars):
        self.value = value
        self.name = name
        self.truename = truename if truename else u""
        self.falsename = falsename if falsename else u""
        self.defaultvalue = defaultvalue
        self.spchars = spchars

    def __nonzero__(self):
        return self.value

    def redraw_cards(self):
        """対応するメニューカードの再描画処理"""
        cw.data.redraw_cards(self.value, flag=self.name)

    def set(self, value, updatedebugger=True):
        if self.value <> value:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.value = value
            if updatedebugger:
                cw.cwpy.event.refresh_variable(self)

    def reverse(self):
        self.set(not self.value)

    def get_valuename(self, value=None):
        if value is None:
            value = self.value

        if value:
            s = self.truename
        else:
            s = self.falsename

        if s is None:
            return u""
        else:
            return s

def redraw_cards(value, flag=""):
    """フラグに対応するメニューカードの再描画処理"""
    if cw.cwpy.is_autospread():
        drawflag = False

        for mcard in cw.cwpy.get_mcards(flag=flag):
            mcardflag = mcard.is_flagtrue()

            if mcardflag and mcard.status == "hidden":
                drawflag = True
            elif not mcardflag and not mcard.status == "hidden":
                drawflag = True

        if drawflag:
            cw.cwpy.hide_cards(True, flag=flag)
            cw.cwpy.deal_cards(flag=flag)

    elif value:
        cw.cwpy.deal_cards(updatelist=False, flag=flag)
    else:
        cw.cwpy.hide_cards(updatelist=False, flag=flag)

class Step(object):
    def __init__(self, value, name, valuenames, defaultvalue, spchars):
        self.value = value
        self.name = name
        self.valuenames = valuenames
        self.defaultvalue = defaultvalue
        self.spchars = spchars

    def set(self, value, updatedebugger=True):
        value = cw.util.numwrap(value, 0, len(self.valuenames)-1)
        if self.value <> value:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.value = value
            if updatedebugger:
                cw.cwpy.event.refresh_variable(self)

    def up(self):
        if self.value < len(self.valuenames)-1:
            self.set(self.value + 1)

    def down(self):
        if not self.value <= 0:
            self.set(self.value - 1)

    def get_valuename(self, value=None):
        if value is None:
            value = self.value
        value = cw.util.numwrap(value, 0, len(self.valuenames)-1)

        s = self.valuenames[value]
        if s is None:
            return u""
        else:
            return s

#-------------------------------------------------------------------------------
#　宿データ
#-------------------------------------------------------------------------------

class YadoDeletedPathSet(set):
    def __init__(self, yadodir, tempdir):
        self.yadodir = yadodir
        self.tempdir = tempdir
        set.__init__(self)

    def write_list(self):
        if not os.path.isdir(self.tempdir):
            os.makedirs(self.tempdir)
        fpath = cw.util.join_paths(self.tempdir, u"~DeletedPaths.temp")
        with open(fpath, "w") as f:
            f.write("\n".join(map(lambda u: u.encode("utf-8"), self)))
            f.flush()
            f.close()
        dstpath = cw.util.join_paths(self.tempdir, u"DeletedPaths.temp")
        cw.util.rename_file(fpath, dstpath)

    def read_list(self):
        fpath = cw.util.join_paths(self.tempdir, u"DeletedPaths.temp")
        if os.path.isfile(fpath):
            with open(fpath, "r") as f:
                for s in f.xreadlines():
                    s = s.rstrip('\n')
                    if s:
                        self.add(s.decode("utf-8"))
                f.close()
            return True
        else:
            return False

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

        # セーブが必要な状況であればTrue
        self._changed = False

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

        # スキン
        self.skindirname = self.environment.gettext("Property/Skin", cw.cwpy.setting.skindirname)
        skintype = self.environment.gettext("Property/Type", cw.cwpy.setting.skintype)
        skinpath = cw.util.join_paths("Data/Skin", self.skindirname, "Skin.xml")
        if not self.skindirname:
            # スキン指定無し
            supported_skin = False
        elif not os.path.isfile(skinpath):
            s = u"スキン「%s」が見つかりません。" % (self.skindirname)
            cw.cwpy.call_modaldlg("ERROR", text=s)
            supported_skin = False
        else:
            prop = cw.header.GetProperty(skinpath)
            if prop.attrs.get(None, {}).get(u"dataVersion", "0") in cw.SUPPORTED_SKIN:
                supported_skin = True
            else:
                skinname = prop.properties.get("Name", self.skindirname)
                s = u"「%s」は対応していないバージョンのスキンです。%sをアップデートしてください。" % (skinname, cw.APP_NAME)
                cw.cwpy.call_modaldlg("ERROR", text=s)
                supported_skin = False

        if not supported_skin:
            for name in os.listdir(u"Data/Skin"):
                path = cw.util.join_paths(u"Data/Skin", name)
                skinpath = cw.util.join_paths(u"Data/Skin", name, "Skin.xml")

                if os.path.isdir(path) and os.path.isfile(skinpath):
                    try:
                        prop = cw.header.GetProperty(skinpath)
                        if skintype and prop.properties.get("Type", "") <> skintype:
                            continue
                        self.skindirname = name
                        break
                    except:
                        # エラーのあるスキンは無視
                        cw.util.print_ex()
            else:
                self.skindirname = cw.cwpy.setting.skindirname
                skintype = cw.cwpy.setting.skintype

            self.set_skinname(self.skindirname, skintype)

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
        self.sort_parties()

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

        # パーティ記録
        self.partyrecord = self.yadodb.get_partyrecord()
        self.sort_partyrecord()

        # 保存済みJPDCイメージ
        self.savedjpdcimage = self.yadodb.get_savedjpdcimage()

        self.yadodb.close()

        # ブックマーク
        self.bookmarks = []
        for be in self.environment.getfind("Bookmarks", raiseerror=False):
            if be.tag <> "Bookmark":
                continue
            bookmark = []
            for e in be.getfind("."):
                bookmark.append(e.text if e.text else "")
            bookmarkpath = be.get("path", None)
            if bookmarkpath is None and bookmark:
                # 0.12.2以前のバージョンではフルパスが記録されていない場合があるので
                # ここで探して記録する(見つからなかった場合は記録しない)
                bookmarkpath = find_scefullpath(cw.cwpy.setting.get_scedir(), bookmark)
                if bookmarkpath:
                    be.set("path", bookmarkpath)
                    self.environment.is_edited = True

            self.bookmarks.append((bookmark, bookmarkpath))

        # シナリオ履歴
        sctempdir = cw.util.join_paths(cw.tempdir, u"Scenario")
        self.recenthistory = cw.setting.RecentHistory(sctempdir)

        # 現在選択中のパーティをセット
        optparty = cw.OPTIONS.party
        cw.OPTIONS.party = ""
        loadparty &= self.environment.getbool("Property/NowSelectingParty", "autoload", True)
        self.party = None
        if loadparty or optparty:
            pname = self.environment.gettext("Property/NowSelectingParty", "")
            if optparty:
                # 起動オプションでパーティが選択されている
                pdppath = cw.util.join_paths(self.yadodir, u"Party")
                pdpath = cw.util.join_paths(pdppath, optparty)
                if os.path.isdir(pdpath):
                    pfile = cw.util.join_paths(pdpath, u"Party.xml")
                    if not os.path.isfile(pfile):
                        # 古いデータではParty.xmlでない場合があるのでXMLファイルを探す
                        for fname in os.listdir(pdpath):
                            if os.path.splitext(fname)[1].lower() == ".xml":
                                pfile = cw.util.join_paths(pdpath, fname)
                                break

                    pname = cw.util.relpath(pfile, self.yadodir)

            if pname:
                path = cw.util.join_paths(self.yadodir, pname)
                seq = [header for header in self.partys if path == header.fpath]

                if seq:
                    self.load_party(seq[0])
                else:
                    cw.OPTIONS.scenario = ""
                    self.load_party(None)

            else:
                cw.OPTIONS.scenario = ""
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
                party = xml2etree(cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party", os.path.basename(fpath)))
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

                    path = cw.util.relpath(carddata.fpath, dpath)
                    path = cw.util.join_paths(path)
                    files.append(cw.data.make_element("File", path))

                # 新フォーマットの荷物袋ログ
                path = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Backpack.xml")
                etree = CWPyElementTree(element=files)
                etree.write(path)

                party.getroot().remove(party.find("Backpack"))
                party.write()
                shutil.move(party.fpath, cw.util.join_paths(cw.tempdir, u"ScenarioLog/Party/Party.xml"))

                wslpath2 = cw.util.join_paths(dpath, "Party.wsl")
                cw.util.compress_zip(cw.util.join_paths(cw.tempdir, u"ScenarioLog"), wslpath2, unicodefilename=True)
                cw.util.remove(cw.util.join_paths(cw.tempdir, u"ScenarioLog"))

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
                        if e2.tag == "ImagePath" and e2.text and not cw.binary.image.path_is_code(e2.text):
                            path = cw.util.join_paths(self.yadodir, e2.text)
                            if os.path.isfile(path):
                                with open(path, "rb") as f:
                                    imagedata = f.read()
                                    f.close()
                                e2.text = cw.binary.image.data_to_code(imagedata)
                    header.imgpaths = cw.image.get_imageinfos(carddata.find("Property"))

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

    def is_empty(self):
        return not (self.partys or self.standbys or self.storehouse or\
                    self.album or self.partyrecord or self.savedjpdcimage or\
                    self.get_gossips() or self.get_compstamps())

    def set_skinname(self, skindirname, skintype):
        self.skindirname = skindirname
        e = self.environment.find("Property/Skin")
        if e is None:
            prop = self.environment.find("Property")
            prop.append(make_element("Skin", skindirname))
        else:
            e.text = skindirname

        e = self.environment.find("Property/Type")
        if e is None:
            prop = self.environment.find("Property")
            prop.append(make_element("Type", skintype))
        else:
            e.text = skintype

        self.environment.is_edited = True

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

    def add_standbys(self, path, sort=True):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        header = self.create_advheader(path)
        header.order = cw.util.new_order(self.standbys)
        self.standbys.append(header)
        if sort:
            self.sort_standbys()
        return header

    def add_album(self, path):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        header = self.create_advheader(path, True)
        self.album.append(header)
        cw.util.sort_by_attr(self.album, "name")
        return header

    def add_party(self, party, sort=True):
        fpath = party.path
        header = self.create_partyheader(fpath)
        header.data = party # 保存時まで記憶しておく
        self.partys.append(header)
        header.order = cw.util.new_order(self.partys)
        if sort:
            self.sort_parties()
        return header

    def add_partyrecord(self, partyrecord):
        """パーティ記録を追加する。"""
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        fpath = cw.xmlcreater.create_partyrecord(partyrecord)
        partyrecord.fpath = fpath
        header = cw.header.PartyRecordHeader(partyrecord=partyrecord)
        self.partyrecord.append(header)
        self.sort_partyrecord()
        return header

    def replace_partyrecord(self, partyrecord):
        """partyrecordと同名のパーティ記録を上書きする。
        同名の情報が無かった場合は、追加する。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        for i, header in enumerate(self.partyrecord):
            if header.name == partyrecord.name:
                self.set_partyrecord(i, partyrecord)
                return
        return self.add_partyrecord(partyrecord)

    def set_partyrecord(self, index, partyrecord):
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

    def remove_partyrecord(self, header):
        """パーティ記録を削除する。"""
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.partyrecord.remove(header)
        self.deletedpaths.add(header.fpath)

    def remove_emptypartyrecord(self):
        """メンバが全滅したパーティ記録を削除する。"""
        for header in self.partyrecord[:]:
            for member in header.members:
                if member:
                    break
            else:
                self.partyrecord.remove(header)

    def can_restoreparty(self, partyrecordheader):
        """partyrecordheaderが再結成可能であればTrueを返す。
        """
        for member in partyrecordheader.members:
            if self.can_restore(member):
                return True
        return False

    def can_restore(self, member):
        """memberがパーティの再結成に応じられるかを返す。
        アクティブでないパーティに所属しているなど、
        応じられない場合はFalseを返す。
        """
        for standby in self.standbys:
            if os.path.splitext(os.path.basename(standby.fpath))[0] == member:
                return True
        if self.party:
            # 現在のパーティは再結成の前に解散するため
            # standbysの中にいるのと同様に扱う
            for m in self.party.members:
                if os.path.splitext(os.path.basename(m.fpath))[0] == member:
                    return True
        return False

    def get_restoremembers(self, partyrecordheader):
        """partyrecordheaderの再結成で
        待機メンバでなくなるメンバの一覧を返す。
        """
        seq = []
        for member in partyrecordheader.members:
            for standby in self.standbys:
                if os.path.splitext(os.path.basename(standby.fpath))[0] == member:
                    seq.append(standby)
                    break
        return seq

    def restore_party(self, partyrecordheader):
        """partyrecordheaderからパーティを再結成する。
        現在操作中のパーティがいた場合は解散される。
        結成されたパーティに属するメンバのheaderのlistを返す。
        所属メンバが宿帳に一人も見つからなかった場合は[]を返す。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if cw.cwpy.ydata.party:
            cw.cwpy.dissolve_party(cleararea=False)
        assert not cw.cwpy.ydata.party
        chgarea = not cw.cwpy.areaid in (2, cw.AREA_BREAKUP)

        members = []
        for member in partyrecordheader.members:
            for standby in self.standbys:
                if os.path.splitext(os.path.basename(standby.fpath))[0] == member:
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

        # 荷物袋の内容を復元。カード置場にない場合は復元不可。
        # 最初は作者名・シナリオ名・使用回数を使用して検索するが、
        # それで見つからない場合はカード名と解説のみで検索する。
        e = yadoxml2etree(partyrecordheader.fpath, tag="BackpackRecord")
        for ce in e.getfind("."):
            if ce.tag <> "CardRecord":
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
        self.party.backpack.reverse()
        for order, header in enumerate(self.party.backpack):
            header.order = order
        self.party.sort_backpack()

        cw.cwpy.statusbar.change(False)
        cw.cwpy.draw()
        cw.cwpy.ydata.party._loading = False
        return members

    def create_advheader(self, path="", album=False, element=None):
        """
        path: xmlのパス。
        album: Trueならアルバム用のAdventurerHeaderを作成。
        element: PropertyタグのElement。
        """
        rootattrs = {}
        if not element:
            element = yadoxml2element(path, "Property", rootattrs=rootattrs)

        return cw.header.AdventurerHeader(element, album, rootattrs=rootattrs)

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
        header = self.create_partyheader(cw.util.join_paths(path, "Party.xml"))
        cw.cwpy.load_party(header, chgarea=chgarea)
        cw.cwpy.statusbar.change(False)
        cw.cwpy.draw()

    def sort_standbys(self):
        if cw.cwpy.setting.sort_standbys == "Level":
            cw.util.sort_by_attr(self.standbys, "level", "name", "order")
        elif cw.cwpy.setting.sort_standbys == "Name":
            cw.util.sort_by_attr(self.standbys, "name", "level", "order")
        else:
            cw.util.sort_by_attr(self.standbys, "order")

    def sort_parties(self):
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

    def sort_storehouse(self):
        sort_cards(self.storehouse, cw.cwpy.setting.sort_cards, cw.cwpy.setting.sort_cardswithstar)

    def sort_partyrecord(self):
        cw.util.sort_by_attr(self.partyrecord, "name")

    def save(self):
        """宿データをセーブする。"""
        # カード置場の順序を記憶しておく
        cardorder = {}
        cardtable = {}
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
        for header in self.standbys:
            if header.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(header.fpath, self.yadodir)
            else:
                fpath = cw.util.relpath(header.fpath, self.tempdir)
                header.fpath = header.fpath.replace(self.tempdir, self.yadodir, 1)
            fpath = cw.util.join_paths(fpath)
            adventurerorder[fpath] = header.order
            adventurertable[fpath] = header

        # アルバム(順序情報なし)
        for header in self.album:
            if not header.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(header.fpath, self.tempdir)
                header.fpath = header.fpath.replace(self.tempdir, self.yadodir, 1)

        # ScenarioLog更新
        if cw.cwpy.is_playingscenario():
            logfilepath = cw.cwpy.advlog.logfilepath
            cw.cwpy.sdata.update_log()
            cw.cwpy.advlog.resume_scenario(logfilepath)

        # environment.xml書き出し
        self.environment.write_xml()

        # party.xmlと冒険者のxmlファイル書き出し
        if self.party:
            self.party.write()

        self.deletedpaths.write_list()

        self._transfer_temp()

        # 各パーティの荷物袋のデータを保存する
        def update_backpack(party):
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
            update_backpack(self.party)
        partyorder = {}
        for party in self.partys:
            if party.data:
                update_backpack(party.data)
                if party.fpath.lower().startswith(self.tempdir.lower()):
                    party.fpath = party.fpath.replace(self.tempdir, self.yadodir, 1)
                party.data = None
            partyorder[party.fpath] = party.order

        partyrecord = {}
        for header in self.partyrecord:
            if header.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(header.fpath, self.yadodir)
            else:
                fpath = cw.util.relpath(header.fpath, self.tempdir)
                header.fpath = header.fpath.replace(self.tempdir, self.yadodir, 1)
            partyrecord[fpath] = header

        savedjpdcimage = {}
        for header in self.savedjpdcimage.itervalues():
            if header.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(header.fpath, self.yadodir)
            else:
                fpath = cw.util.relpath(header.fpath, self.tempdir)
                header.fpath = header.fpath.replace(self.tempdir, self.yadodir, 1)
            savedjpdcimage[fpath] = header

        # カードデータベースを更新
        @synclock(_lock)
        def update_database(yadodir):
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
        cw.cwpy.draw()
        self._changed = False

    def _retry_save(self):
        """TempからYadoへの転送中に失敗した保存処理を再実行する。
        """
        if self.deletedpaths.read_list():
            self._transfer_temp()

    def _transfer_temp(self):
        # TEMPのファイルを移動
        deltempfpath = cw.util.join_paths(self.deletedpaths.tempdir, u"DeletedPaths.temp")
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
        delfailurepaths = set()
        for path in self.deletedpaths:
            if os.path.normpath(os.path.normcase(path)) in ignores:
                continue
            cw.util.remove(path)
            dpath = os.path.dirname(path)
            if dpath.startswith(materialdir) and os.path.isdir(dpath)\
                                                    and not os.listdir(dpath):
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
            if cw.cwpy.ydata:
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
            if cw.cwpy.ydata:
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
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.environment.remove("CompleteStamps", e)

        if elements and cw.cwpy.is_playingscenario():
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
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.environment.remove("Gossips", e)

        if elements and cw.cwpy.is_playingscenario():
            if cw.cwpy.sdata.gossips.get(name) is True:
                cw.cwpy.sdata.gossips.pop(name)
            else:
                cw.cwpy.sdata.gossips[name] = False

    def clear_compstamps(self):
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

    def clear_gossips(self):
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

    def set_money(self, value, blink=False):
        """金庫に入っている金額を変更する。
        現在の所持金にvalue値をプラスするので注意。
        """
        if value <> 0:
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

    #---------------------------------------------------------------------------
    # パーティ連れ込み
    #---------------------------------------------------------------------------

    def join_npcs(self):
        """
        シナリオのNPCを宿に連れ込む。
        """
        r_gene = re.compile(u"＠Ｇ\d{10}$")
        for fcard in cw.cwpy.get_fcards():
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            fcard.set_fullrecovery()

            # 必須クーポンを所持していなかったら補填
            if not fcard.has_age() or not fcard.has_sex():
                cw.cwpy.play_sound("signal")
                cw.cwpy.call_modaldlg("DATACOMP", ccard=fcard)

            # システムクーポン
            fcard.set_coupon(u"＿" + fcard.name, fcard.level * (fcard.level-1))
            fcard.set_coupon(u"＠レベル原点", fcard.level)
            fcard.set_coupon(u"＠ＥＰ", 0)
            talent = fcard.get_talent()

            value = 10
            for nature in cw.cwpy.setting.natures:
                if u"＿" + nature.name == talent:
                    value = nature.levelmax
                    break

            fcard.set_coupon(u"＠本来の上限", value)
            for coupon in fcard.get_coupons():
                if r_gene.match(coupon):
                    break
            else:
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
                                                    "Material", cardtype, name if name else"noname")
                    dstdir = cw.util.dupcheck_plus(dstdir)
                    can_loaded_scaledimage = e.getbool(".", "scaledimage", False)
                    cw.cwpy.copy_materials(e, dstdir, can_loaded_scaledimage=can_loaded_scaledimage)

            # カード画像コピー
            name = cw.util.repl_dischar(fcard.name) if fcard.name else "noname"
            e = data.getfind("Property")
            dstdir = cw.util.join_paths(self.yadodir,
                                                "Material", "Adventurer", name)
            dstdir = cw.util.dupcheck_plus(dstdir)
            can_loaded_scaledimage = data.getbool(".", "scaledimage", False)
            cw.cwpy.copy_materials(e, dstdir, can_loaded_scaledimage=can_loaded_scaledimage)
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
            if not os.path.isdir(dpath):
                continue

            for dname in os.listdir(dpath):
                dpath2 = cw.util.join_paths(dpath, dname)
                if not os.path.isdir(dpath2):
                    continue

                for name in os.listdir(dpath2):
                    path = cw.util.join_paths(dpath2, name)
                    if name.endswith(".wsl") and os.path.isfile(path)\
                                        and not path in self.deletedpaths:
                        e = cw.util.get_elementfromzip(path, "ScenarioLog.xml",
                                                                    "Property")
                        path = e.gettext("WsnPath")
                        path = cw.util.get_linktarget(path)
                        path = os.path.normcase(os.path.normpath(os.path.abspath(path)))
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

    #---------------------------------------------------------------------------
    # ブックマーク
    #---------------------------------------------------------------------------

    def add_bookmark(self, spaths, path):
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

    def set_bookmarks(self, bookmarks):
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

def find_scefullpath(scepath, spaths):
    """開始ディレクトリscepathから経路spathsを
    辿った結果得られたフルパスを返す。
    辿れなかった場合は""を返す。
    """
    bookmarkpath = u""
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
    def __init__(self, header, partyinfoonly=True):
        path = header.fpath

        # True時は、エリア移動中にPlayerCardスプライトを新規作成する
        self._loading = True

        self.members = []
        if not header.data:
            self.backpack = []
            self.backpack_moved = []
        self.path = path

        # キャンセル可能な対象消去メンバ(互換機能)
        self.vanished_pcards = []

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
                for header in carddb.get_cards():
                    if header.moved == 0:
                        self.backpack.append(header)
                    else:
                        self.backpack_moved.append(header)
                carddb.close()
            self.sort_backpack()

    def sort_backpack(self):
        sort_cards(self.backpack, cw.cwpy.setting.sort_cards, cw.cwpy.setting.sort_cardswithstar)

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
            s.update(header.get_keycodes())

        s.discard("")
        return s

    def has_keycode(self, keycode, skill=True, item=True, beast=True, hand=True):
        """指定されたキーコードを所持しているか。"""
        for header in self.backpack:
            if not skill and header.type == "SkillCard":
                continue
            elif not item and header.type == "ItemCard":
                continue
            elif not beast and header.type == "BeastCard":
                continue

            if keycode in header.get_keycodes():
                return True

        return False

    def get_relpath(self):
        ppath = os.path.dirname(self.path)
        if ppath.lower().startswith("yado"):
            relpath = cw.util.relpath(ppath, cw.cwpy.yadodir)
        else:
            relpath = cw.util.relpath(ppath, cw.cwpy.tempdir)
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
        if cw.cwpy.ydata:
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
                if i <> pcard.index:
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
        cw.animation.animate_sprite(pcard, "deal")

    def remove(self, pcard):
        """
        メンバーを削除する。引数はPlayerCard。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        pcard.remove_numbercoupon()
        self.members.remove(pcard.data)
        if cw.cwpy.cardgrp.has(pcard):
            cw.cwpy.cardgrp.remove(pcard)
            cw.cwpy.pcards.remove(pcard)
        self.data.getfind("Property/Members").clear()

        for pcard in cw.cwpy.get_pcards():
            s = os.path.basename(pcard.data.fpath)
            s = cw.util.splitext(s)[0]
            e = self.data.make_element("Member", s)
            self.data.append("Property/Members", e)

    def replace_order(self, index1, index2):
        """
        メンバーの位置を入れ替える。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        seq = cw.cwpy.get_pcards()
        assert len(seq) == len(self.members)
        seq[index1], seq[index2] = seq[index2], seq[index1]
        self.members[index1], self.members[index2] = self.members[index2], self.members[index1]
        for index, pcard in enumerate(seq):
            pcard.index = index
            pcard.layer = (pcard.layer[0], pcard.layer[1], index, pcard.layer[3])
            cw.cwpy.cardgrp.change_layer(pcard, pcard.layer)
        cw.cwpy.pcards = seq

        self.data.getfind("Property/Members").clear()
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

    def set_name(self, name):
        """
        パーティ名を変更する。
        """
        if self.name <> name:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            oldname = self.name
            self.name = name
            self.data.edit("Property/Name", name)
            cw.cwpy.advlog.rename_party(self.name, oldname)
            cw.cwpy.background.reload(False, nocheckvisible=True)

    def set_money(self, value, fromevent=False, blink=False):
        """
        パーティの所持金を変更する。
        """
        if value <> 0:
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

    def suspend_levelup(self, suspend):
        """
        レベルアップの可否を設定する。
        """
        if suspend <> self.is_suspendlevelup:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.is_suspendlevelup = suspend
            e = self.data.find("Property/SuspendLevelUp")
            if e is None:
                pe = self.data.find("Property")
                pe.append(make_element("SuspendLevelUp", str(suspend)))
                self.data.is_edited = True
            else:
                self.data.edit("Property/SuspendLevelUp", str(suspend))

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
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        for card in self.backpack[:]:
            cw.cwpy.trade("TRASHBOX", header=card, from_event=True, sort=False)
        for pcard in cw.cwpy.get_pcards():
            pcard.lost()
        self.members = []

        cw.cwpy.remove_xml(self)
        cw.cwpy.ydata.deletedpaths.add(os.path.dirname(self.path))

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
        path = cw.util.splitext(self.data.fpath)[0] + ".wsl"
        return bool(cw.util.get_yadofilepath(path))

    def get_sceheader(self):
        """
        現在冒険中のシナリオのScenarioHeaderを返す。
        """
        path = cw.util.splitext(self.data.fpath)[0] + ".wsl"
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

    def set_lastscenario(self, lastscenario, lastscenariopath):
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

def sort_cards(cards, condition, withstar):
    seq = []
    if withstar:
        seq.append("negastar")

    def addetckey():
        for key in ("name", "scenario", "author", "type_id", "level", "sellingprice"):
            if key <> seq[0]:
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
    seq.append("order")

    cw.util.sort_by_attr(cards, *seq)

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
            text = e.text
            if text is None:
                text = u""

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

    def __init__(self, tag, attrib={}.copy()):
        _ElementInterface.__init__(self, tag, attrib)
        # CWXパスを構築するための親要素情報
        self.cwxparent = None
        self.content = None
        self.nextelements = None
        self.needcheck = None
        self.cwxpath = None
        self._cwxline_index = None

    def append(self, subelement):
        subelement.cwxparent = self
        return _ElementInterface.append(self, subelement)

    def extend(self, subelements):
        for subelement in subelements:
            subelement.cwxparent = self
        return _ElementInterface.extend(self, subelements)

    def insert(self, index, subelement):
        subelement.cwxparent = self
        return _ElementInterface.insert(self, index, subelement)

    def remove(self, subelement):
        if subelement.cwxparent is self:
            subelement.cwxparent = None
        return _ElementInterface.remove(self, subelement)

    def clear(self):
        for subelement in self:
            subelement.cwxparent = None
        return _ElementInterface.clear(self)

    def index(self, subelement):
        for i, e in enumerate(self):
            if e == subelement:
                return i
        return -1

    def get_cwxpath(self):
        """CWXパスを構築して返す。
        イベントまたはその親要素でなければ正しいパスは構築されない。
        """
        if not self.cwxpath is None:
            return self.cwxpath

        cwxpath = []

        e = self
        scenariodata = False
        while not e is None:
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
                cwxpath.append("menucard:%s" % (e.cwxparent.index(e)))
            elif e.tag == "EnemyCard":
                cwxpath.append("enemycard:%s" % (e.cwxparent.index(e)))
            elif e.tag == "Event":
                cwxpath.append("event:%s" % (e.cwxparent.index(e)))
            elif e.tag == "Motion":
                cwxpath.append("motion:%s" % (e.cwxparent.index(e)))
            elif e.tag in ("SkillCards", "ItemCards", "BeastCards", "Beasts", "Motions",
                           "Contents", "Events", "MenuCards", "EnemyCards"):
                pass
            elif e.tag in ("Adventurer", "CastCards", "System"):
                break
            elif e.tag == "PlayerCardEvents":
                # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
                cwxpath.append("playercard:%s" % (e.cwxparent.index(e)))
            else:
                # Content
                assert not e.cwxparent is None, e.tag
                assert e.cwxparent.tag in ("Contents", "ContentsLine"), "%s/%s" % (e.cwxparent.tag, e.tag)
                if e.cwxparent.tag == "ContentsLine":
                    if e._cwxline_index is None:
                        for i, line_child in enumerate(e.cwxparent):
                            line_child._cwxline_index = i
                    assert not e._cwxline_index is None
                    for _i in xrange(e._cwxline_index):
                        cwxpath.append(":0")
                else:
                    cwxpath.append(":%s" % (e.cwxparent.index(e)))

            e = e.cwxparent

        if scenariodata:
            self.cwxpath = "/".join(reversed(cwxpath))
        else:
            self.cwxpath = ""

        return self.cwxpath


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

        retry = 0
        while retry < 5:
            try:
                with io.BytesIO() as f:
                    f.write('<?xml version="1.0" encoding="utf-8" ?>\n')
                    ElementTree.write(self, f, "utf-8")
                    sbytes = f.getvalue()
                    f.close()
                with open(path, "wb") as f:
                    f.write(sbytes)
                    f.flush()
                    f.close()
                    break
            except IOError, ex:
                if 5 <= retry:
                    raise ex
                cw.util.print_ex()
                retry += 1
                time.sleep(1)

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
                t = (self.fpath, path, value, attrname)
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
            if not element.text:
                element.text = i + " "

            if not element.tail:
                element.tail = i if depth else None

            for element in element:
                self.form_element(element, depth + 1)

            if not element.tail:
                element.tail = i

        else:
            if not element.text:
                element.text = None

            if not element.tail:
                element.tail = i if depth else None

#-------------------------------------------------------------------------------
# xmlパーサ
#-------------------------------------------------------------------------------

def make_element(name, text="", attrs={}.copy(), tail=""):
    element = CWPyElement(name, attrs)
    element.text = text
    element.tail = tail
    return element

def yadoxml2etree(path, tag="", rootattrs=None):
    element = yadoxml2element(path, tag, rootattrs=rootattrs)
    return CWPyElementTree(element=element)

def yadoxml2element(path, tag="", rootattrs=None):
    yadodir = cw.util.join_paths(cw.tempdir, u"Yado")
    if path.startswith("Yado"):
        temppath = path.replace("Yado", yadodir, 1)
    elif path.startswith(yadodir):
        temppath = path
        path = path.replace(yadodir, "Yado", 1)
    else:
        raise ValueError("%s is not YadoXMLFile." % path)

    if os.path.isfile(temppath):
        return xml2element(temppath, tag, rootattrs=rootattrs)
    elif os.path.isfile(path):
        return xml2element(path, tag, rootattrs=rootattrs)
    else:
        raise ValueError("%s is not found." % path)

def xml2etree(path="", tag="", stream=None, element=None, nocache=False):
    if element is None:
        element = xml2element(path, tag, stream, nocache=nocache)

    return CWPyElementTree(element=element)

def xml2element(path="", tag="", stream=None, nocache=False, rootattrs=None):
    usecache = path and cw.cwpy and cw.cwpy.sdata and\
               isinstance(cw.cwpy.sdata, cw.data.ScenarioData) and\
               path.startswith(cw.cwpy.sdata.tempdir)
    if usecache:
        mtime = os.path.getmtime(path)

    # キャッシュからデータを取得
    if usecache and path in cw.cwpy.sdata.data_cache:
        cachedata = cw.cwpy.sdata.data_cache[path]
        if mtime <= cachedata.mtime:
            data = cachedata.data
            if not rootattrs is None:
                for key, value in data.attrib.iteritems():
                    rootattrs[key] = value
            if tag:
                data = data.find(tag)
            if nocache:
                # 変更されてもよいデータを返す
                return copydata(data)
            return data

    data = None
    versionhint = None
    if not stream and cw.cwpy and cw.cwpy.classicdata:
        # クラシックなシナリオのファイルだった場合は変換する
        lpath = path.lower()
        if lpath.endswith(".wsm") or lpath.endswith(".wid"):
            cdata, filedata = cw.cwpy.classicdata.load_file(path)
            if cdata is None:
                return None
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

    basedata = data
    if not rootattrs is None:
        for key, value in data.attrib.iteritems():
            rootattrs[key] = value
    if tag:
        data = data.find(tag)

    if usecache:
        # キャッシュにデータを保存
        cachedata = CacheData(basedata, mtime)
        cw.cwpy.sdata.data_cache[path] = cachedata
        if nocache:
            data = copydata(data)

    if cw.cwpy:
        basehint = cw.cwpy.sct.to_basehint(versionhint)
        if basehint:
            prop = data.find("Property")
            if not prop is None:
                prop.set("versionHint", basehint)

    return data

class CacheData(object):
    def __init__(self, data, mtime):
        self.data = data
        self.mtime = mtime

def copydata(data):
    if isinstance(data, CWPyElementTree):
        return CWPyElementTree(element=copydata(data.getroot()))

    if data.tag in ("Motions", "Events", "Id", "Name",
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

class EndTargetTagException(Exception):
    pass

class SimpleXmlParser(object):
    def __init__(self, fpath, targettag="", stream=None, targetonly=False,
                 rootattrs=None):
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

    def _clear_attrs(self):
        self.root = None
        self.node_stack = []
        self.parsetags = []
        self.currenttags = []
        if self.rootattrs:
            self.rootattrs.clear()
        self._persed = False

    def start_element(self, name, attrs):
        """要素の開始。"""
        if not self.currenttags:
            if not self.rootattrs is None:
                for key, value in attrs.iteritems():
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
            if data:
                element = self.node_stack[-1]

                if element.text:
                    pass
                else:
                    element.text = data

    def parse(self):
        if hasattr(self.file, "read"):
            self.parse_file(self.file)
        else:
            with open(self.fpath, "rb") as f:
                self.parse_file(f)
                f.close()

        root = self.root
        return root

    def parse_file(self, fname):
        try:
            self._parse_file(fname)
        except EndTargetTagException:
            pass
        except xml.parsers.expat.ExpatError, err:
            # エラーになったファイルのパスを付け加える
            s = u". file: " + self.fpath
            err.args = (err.args[0] + s.encode(u"utf-8"), )
            raise err

    def _create_parser(self):
        parser = xml.parsers.expat.ParserCreate()
        parser.buffer_text = 1
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.char_data
        return parser

    def _parse_file(self, fname):
        parser = self._create_parser()
        fdata = fname.read()
        try:
            parser.Parse(fdata, 1)
        except xml.parsers.expat.ExpatError:
            # たまに制御文字が混入しているシナリオがある
            fdata = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", fdata)
            self._clear_attrs()
            parser = self._create_parser()
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
