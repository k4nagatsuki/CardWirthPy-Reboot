#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import copy
import math
import shutil
import itertools
import threading

import cw
from cw.util import synclock


_couponlock = threading.Lock()

class Character(object):
    def __init__(self, data=None):
        if not data is None:
            self.data = data
        self.reversed = False

        # 名前
        self.name = self.data.gettext("Property/Name", "")
        # レベル
        self.level = cw.util.numwrap(self.data.getint("Property/Level", 1), 1, 65536)
        # 各種所持カードのリスト
        self.cardpocket = self.get_cardpocket()
        # 全てホールド
        self.hold_all = [
            self.data.getbool("SkillCards", "hold_all", False),
            self.data.getbool("ItemCards", "hold_all", False),
            self.data.getbool("BeastCards", "hold_all", False),
        ]
        # 現在ライフ・最大ライフ
        self.life = max(0, self.data.getint("Property/Life", 0))
        self.maxlife = max(1, self.data.getint("Property/Life", "max", 1))
        self.life = min(self.maxlife, self.life)
        # 精神状態
        self.mentality = self.data.gettext("Property/Status/Mentality", "Normal")
        self.mentality_dur = cw.util.numwrap(self.data.getint("Property/Status/Mentality",
                                                                    "duration", 0), 0, 999)
        if self.mentality_dur == 0 or self.mentality == "Normal":
            self.mentality = "Normal"
            self.mentality_dur = 0
        # 麻痺値
        self.paralyze = cw.util.numwrap(self.data.getint("Property/Status/Paralyze", 0), 0, 40)
        # 中毒値
        self.poison = cw.util.numwrap(self.data.getint("Property/Status/Poison", 0), 0, 40)
        # 束縛時間値
        self.bind = cw.util.numwrap(self.data.getint("Property/Status/Bind", "duration", 0), 0, 999)
        # 沈黙時間値
        self.silence = cw.util.numwrap(self.data.getint("Property/Status/Silence", "duration", 0), 0, 999)
        # 暴露時間値
        self.faceup = cw.util.numwrap(self.data.getint("Property/Status/FaceUp", "duration", 0), 0, 999)
        # 魔法無効時間値
        self.antimagic = cw.util.numwrap(self.data.getint("Property/Status/AntiMagic",
                                                                    "duration", 0), 0, 999)
        # 行動力強化値
        self.enhance_act = cw.util.numwrap(self.data.getint("Property/Enhance/Action", 0), -10, 10)
        self.enhance_act_dur = cw.util.numwrap(self.data.getint("Property/Enhance/Action",
                                                                    "duration", 0), 0, 999)
        if self.enhance_act == 0 or self.enhance_act_dur == 0:
            self.enhance_act = 0
            self.enhance_act_dur = 0
        # 回避力強化値
        self.enhance_avo = cw.util.numwrap(self.data.getint("Property/Enhance/Avoid", 0), -10, 10)
        self.enhance_avo_dur = cw.util.numwrap(self.data.getint("Property/Enhance/Avoid",
                                                                    "duration", 0), 0, 999)
        if self.enhance_avo == 0 or self.enhance_avo_dur == 0:
            self.enhance_avo = 0
            self.enhance_avo_dur = 0
        # 抵抗力強化値
        self.enhance_res = cw.util.numwrap(self.data.getint("Property/Enhance/Resist", 0), -10, 10)
        self.enhance_res_dur = cw.util.numwrap(self.data.getint("Property/Enhance/Resist",
                                                                    "duration", 0), 0, 999)
        if self.enhance_res == 0 or self.enhance_res_dur == 0:
            self.enhance_res = 0
            self.enhance_res_dur = 0
        # 防御力強化値
        self.enhance_def = cw.util.numwrap(self.data.getint("Property/Enhance/Defense", 0), -10, 10)
        self.enhance_def_dur = cw.util.numwrap(self.data.getint("Property/Enhance/Defense",
                                                                    "duration", 0), 0, 999)
        if self.enhance_def == 0 or self.enhance_def_dur == 0:
            self.enhance_def = 0
            self.enhance_def_dur = 0
        # 各種能力値
        e = self.data.getfind("Property/Ability/Physical")
        self.physical = copy.copy(e.attrib)
        e = self.data.getfind("Property/Ability/Mental")
        self.mental = copy.copy(e.attrib)
        e = self.data.getfind("Property/Ability/Enhance")
        self.enhance = copy.copy(e.attrib)

        for key, value in self.physical.iteritems():
            try:
                self.physical[key] = cw.util.numwrap(float(value), 0, 65536)
            except:
                self.physical[key] = 0
        for key, value in self.mental.iteritems():
            try:
                self.mental[key] = cw.util.numwrap(float(value), -65536, 65536)
            except:
                self.mental[key] = 0
        for key, value in self.enhance.iteritems():
            try:
                self.enhance[key] = cw.util.numwrap(float(value), -10, 10)
            except:
                self.enhance[key] = 0

        # 特性
        e = self.data.getfind("Property/Feature/Type")
        self.feature = copy.copy(e.attrib)
        e = self.data.getfind("Property/Feature/NoEffect")
        self.noeffect = copy.copy(e.attrib)
        e = self.data.getfind("Property/Feature/Resist")
        self.resist = copy.copy(e.attrib)
        e = self.data.getfind("Property/Feature/Weakness")
        self.weakness = copy.copy(e.attrib)

        for d in (self.feature, self.noeffect, self.resist, self.weakness):
            for key, value in d.iteritems():
                try:
                    d[key] = cw.util.str2bool(value)
                except:
                    d[key] = False

        # デッキ
        self.deck = cw.deck.Deck(self)
        # 戦闘行動(Target, CardHeader)
        self.actiondata = None
        self.actionautoselected = False
        # 行動順位を決定する数値
        self.actionorder = 0
        # ラウンド処理中で行動開始前ならTrue
        self.actionend = True

        self.reversed = False

        # クーポン一覧
        self.coupons = {}
        for e in self.data.getfind("Property/Coupons"):
            if not e.text:
                continue

            if e.text in (u"＠効果対象", u"イベント対象", u"使用者"):
                # 効果・イベント対象に付与されるシステムクーポン(Wsn.2)
                continue

            try:
                self.coupons[e.text] = int(e.get("value")), e
            except:
                self.coupons[e.text] = 0, e
            if e.text == u"：Ｒ":
                self.reversed = True
        # 時限クーポンのデータのリスト(name, flag_countable)
        self.timedcoupons = self.get_timedcoupons()

        # 対象消去されたか否か
        self._vanished = False
        # 互換性マーク
        self.versionhint = cw.cwpy.sct.from_basehint(self.data.getattr("Property", "versionHint", ""))

        # 状態の正規化
        self.cardimg = None
        if self.is_unconscious():
            # 最初から意識不明の場合、基本的に全てのステータスが
            # クリアされるが、唯一、回数制限つきの付帯能力だけは、
            # 後から意識不明になった時と違ってクリアされない(CardWirth 1.50)
            self.set_unconsciousstatus(clearbeast=False)

        # 適性検査用のCardHeader。
        self.test_aptitude = None

        # キャッシュ
        self._voc_tbl = {}

    def get_imagepaths(self):
        """現在表示中のカード画像の情報を
        cw.image.ImageInfoのlistで返す。
        """
        data = self.data.find("Property")
        return cw.image.get_imageinfos(data)

    def set_images(self, paths):
        """このキャラクターのカード画像を
        cw.image.ImageInfoのlistで指定した内容に差し替える。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        etree = None
        eimg = None
        infos = self.get_imagepaths()
        can_loaded_scaledimage = self.data.getattr(".", "scaledimage", False)
        if infos:
            if cw.cwpy.is_playingscenario():
                # メッセージログのイメージが変化しないように
                # ファイル上書き前に読み込んでおく
                for info in infos:
                    if not info.path:
                        continue
                    fpath = info.path
                    fname = os.path.basename(fpath)
                    fpath2 = cw.util.join_yadodir(fpath)
                    if os.path.isfile(fpath2):
                        cw.sprite.message.store_messagelogimage(fpath2, can_loaded_scaledimage)

                # F9のためにシナリオ突入時の画像の記録を取る
                name = os.path.splitext(os.path.basename(self.data.fpath))[0]
                log = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Face/Log.xml")
                if os.path.isfile(log):
                    etree = cw.data.xml2etree(log)
                else:
                    e = cw.data.make_element("FaceLog", "")
                    etree = cw.data.xml2etree(element=e)
                    etree.fpath = log
                for e in etree.getfind(".", raiseerror=False):
                    member = e.getattr(".", "member")
                    if member == name:
                        # すでに記録済み
                        eimg = e
                        break
                else:
                    e = cw.data.make_element("ImagePaths", u"", {"member":name})
                    eimg = e
                    dpath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/Face")
                    for info in infos:
                        if not info.path:
                            continue
                        fpath = info.path
                        fname = os.path.basename(fpath)
                        fpath2 = cw.util.join_yadodir(fpath)
                        if os.path.isfile(fpath2):
                            fpath = cw.util.join_paths(dpath, fname)
                            fpath = cw.util.dupcheck_plus(fpath, yado=False)
                            if not os.path.isdir(dpath):
                                os.makedirs(dpath)
                            cw.util.copy_scaledimagepaths(fpath2, fpath, can_loaded_scaledimage)
                            e2 = cw.data.make_element("ImagePath", os.path.basename(fpath))
                            info.set_attr(e2)
                            e.append(e2)

                    etree.getroot().append(e)

            for info in infos:
                if not info.path:
                    continue
                fpath = cw.util.join_yadodir(info.path)
                for fpath, _scale in cw.util.get_scaledimagepaths(fpath, can_loaded_scaledimage):
                    cw.cwpy.ydata.deletedpaths.add(fpath, forceyado=True)

        if not eimg is None:
            # 複数回変更された時は変更後ファイル情報を
            # 都度最新に更新しておく
            for e in list(eimg):
                if e.tag == "NewImagePath":
                    eimg.remove(e)

        # 新しいファイル群をコピー
        newpaths = cw.xmlcreater.write_castimagepath(self.get_name(), paths, True)
        prop = self.data.find("Property")
        for ename in ("ImagePath", "ImagePaths"):
            e = prop.find(ename)
            if not e is None:
                prop.remove(e)
        # コピー後のファイルパスを設定
        e = cw.data.make_element("ImagePaths", "")
        prop.append(e)
        for info in newpaths:
            if info.path:
                e2 = cw.data.make_element("ImagePath", info.path)
                info.set_attr(e2)
                e.append(e2)

                if not eimg is None:
                    # F9時に変更後のイメージを削除するため、記録しておく
                    eimg.append(cw.data.make_element("NewImagePath", info.path))

        # 外部から設定したイメージは常にスケーリング可能とする
        self.data.edit(".", str(True), "scaledimage")

        self.data.is_edited = True

        if not etree is None:
            etree.write()

        return newpaths

    def get_name(self):
        return self.data.gettext("Property/Name", "")

    def set_name(self, name):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Name", name)
        self.name = name

    def get_description(self):
        return cw.util.decodewrap(self.data.gettext("Property/Description", ""))

    def set_description(self, desc):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Description", cw.util.encodewrap(desc))

    def set_maxlife(self, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        v = float(self.life) / self.maxlife
        self.maxlife = value
        self.data.edit("Property/Life", str(int(value)), "max")
        if self.life <> 0:
            self.life = max(1, int(self.maxlife * v))
            self.data.edit("Property/Life", str(int(self.maxlife)))

        if self.data.getattr("Property/Life", "coefficient", 0):
            self.data.remove("Property/Life", attrname="coefficient")

    def set_physical(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Ability/Physical", str(int(value)), name)
        self.physical[name] = float(value)
        self._clear_vocationcache()

    def set_mental(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Ability/Mental", str(value), name)
        self.mental[name] = float(value)
        self._clear_vocationcache()

    def set_feature(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Feature/Type", str(value), name)
        self.feature[name] = value

    def set_noeffect(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Feature/NoEffect", str(value), name)
        self.noeffect[name] = value

    def set_resist(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Feature/Resist", str(value), name)
        self.resist[name] = value

    def set_weakness(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Feature/Weakness", str(value), name)
        self.weakness[name] = value

    def set_enhance(self, name, value):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.data.edit("Property/Ability/Enhance", str(value), name)
        self.enhance[name] = value

    def get_cardpocket(self):
        flag = bool(self.data.getroot().tag == "CastCard")
        maxnums = self.get_cardpocketspace()
        paths = ("SkillCards", "ItemCards", "BeastCards")
        cardpocket = []

        for maxn, path in zip(maxnums, paths):
            headers = []

            pe = self.data.find(path)
            if not pe is None:
                for e in pe:
                    if maxn <= len(headers):
                        # 最大所持数を越えたカードは消去
                        break
                    e = cw.cwpy.sdata.get_carddata(e, inusecard=False)
                    if e is None:
                        continue
                    header = cw.header.CardHeader(owner=self, carddata=e,
                                                                from_scenario=flag)
                    headers.append(header)

                # 参照先に差し替えられている可能性があるので
                # ここでpeの子要素を入れ替える
                for e in list(pe):
                    pe.remove(e)
                for header in headers:
                    pe.append(header.carddata)

            cardpocket.append(headers[:maxn])

        return tuple(cardpocket)

    def get_keycodes(self, skill=True, item=True, beast=True):
        """所持カードのキーコード一覧を返す。"""
        s = set()
        seq = []
        if skill:
            seq.append(self.get_pocketcards(cw.POCKET_SKILL))
        if item:
            seq.append(self.get_pocketcards(cw.POCKET_ITEM))
        if beast:
            seq.append(self.get_pocketcards(cw.POCKET_BEAST))

        for header in seq:
            s.update(header.get_keycodes())

        s.discard("")
        return s

    def has_keycode(self, keycode, skill=True, item=True, beast=True, hand=True):
        """指定されたキーコードを所持しているか。"""
        if hand and self.deck:
            # 戦闘時の手札(Wsn.2)
            for header in self.deck.get_hand(self):
                if keycode in header.get_keycodes():
                    return True
        if skill:
            for header in self.get_pocketcards(cw.POCKET_SKILL):
                if keycode in header.get_keycodes():
                    return True
        if item:
            for header in self.get_pocketcards(cw.POCKET_ITEM):
                if keycode in header.get_keycodes():
                    return True
        if beast:
            for header in self.get_pocketcards(cw.POCKET_BEAST):
                if keycode in header.get_keycodes():
                    return True

        return False

    def lost(self):
        """
        対象消去やゲームオーバー時に呼ばれる。
        Playerクラスでオーバーライト。
        """
        pass

    #---------------------------------------------------------------------------
    #　状態チェック用
    #---------------------------------------------------------------------------

    def is_normal(self):
        """
        通常の精神状態かどうかをbool値で返す。
        """
        return bool(self.mentality == "Normal")

    def is_panic(self):
        """
        恐慌状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Panic")

    def is_brave(self):
        """
        勇敢状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Brave")

    def is_overheat(self):
        """
        激昂状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Overheat")

    def is_confuse(self):
        """
        混乱状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Confuse")

    def is_sleep(self):
        """
        睡眠状態かどうかをbool値で返す
        """
        return bool(self.mentality == "Sleep")

    def is_paralyze(self):
        """
        麻痺または石化状態かどうかをbool値で返す
        """
        return bool(self.paralyze > 0)

    def is_poison(self):
        """
        中毒状態かどうかをbool値で返す
        """
        return bool(self.poison > 0)

    def is_bind(self):
        """
        呪縛状態かどうかをbool値で返す
        """
        return bool(self.bind > 0)

    def is_silence(self):
        """
        沈黙状態かどうかをbool値で返す。
        """
        return bool(self.silence > 0)

    def is_faceup(self):
        """
        暴露状態かどうかをbool値で返す。
        """
        return bool(self.faceup > 0)

    def is_antimagic(self):
        """
        魔法無効状態かどうかをbool値で返す。
        """
        return bool(self.antimagic > 0)

    @staticmethod
    def calc_petrified(paralyze):
        return bool(paralyze > 20)

    def is_petrified(self):
        """
        石化状態かどうかをbool値で返す
        """
        return Character.calc_petrified(self.paralyze)

    def is_unconscious(self):
        """
        意識不明状態かどうかをbool値で返す
        """
        return bool(self.life <= 0)

    @staticmethod
    def calc_heavyinjured(life, maxlife):
        return bool(Character.calc_lifeper(life, maxlife) <= 20 and 0 < life)

    def is_heavyinjured(self):
        """
        重傷状態かどうかをbool値で返す
        """
        return Character.calc_heavyinjured(self.life, self.maxlife)

    @staticmethod
    def calc_injured(life, maxlife):
        return bool(life < maxlife and not Character.calc_heavyinjured(life, maxlife) and 0 < life)

    def is_injured(self):
        """
        軽傷状態かどうかをbool値で返す
        """
        return Character.calc_injured(self.life, self.maxlife)

    def is_injuredall(self):
        """
        負傷状態かどうかをbool値で返す
        """
        return bool(self.life < self.maxlife)

    def is_inactive(self, check_reversed=True):
        """
        行動不可状態かどうかをbool値で返す
        """
        b = self.is_sleep()
        b |= self.is_paralyze()
        b |= self.is_bind()
        b |= self.is_unconscious()
        if check_reversed:
            b |= self.is_reversed()
        return b

    def is_active(self):
        """
        行動可能状態かどうかをbool値で返す
        """
        return not self.is_inactive()

    def is_dead(self):
        """
        非生存状態かどうかをbool値で返す
        """
        b = self.is_paralyze()
        b |= self.is_unconscious()
        b |= self.is_reversed()
        return b

    def is_alive(self):
        """
        生存状態かどうかをbool値で返す
        """
        return not self.is_dead()

    def is_fine(self):
        """
        健康状態かどうかをbool値で返す
        """
        return not self.is_injuredall() and not self.is_unconscious()

    def is_analyzable(self):
        """
        各種データが暴露可能かどうかbool値で返す。
        EnemyCardのための処理。
        デバッグフラグがTrueだったら問答無用で暴露する。
        """
        if isinstance(self, Enemy):
            return cw.cwpy.debug or self.is_faceup()
        else:
            return True

    def is_avoidable(self, use_enhance=True):
        """
        回避判定可能かどうかbool値で返す。
        """
        if use_enhance:
            return self.is_active() and self.get_enhance_avo() > -10
        else:
            return self.is_active()

    def is_resistable(self, use_enhance=True):
        """
        抵抗判定可能かどうかbool値で返す。
        呪縛状態でも抵抗できる。
        """
        b = self.is_sleep()
        b |= self.is_paralyze()
        b |= self.is_unconscious()
        if use_enhance:
            return not b and self.get_enhance_res() > -10
        else:
            return not b

    def is_reversed(self):
        """
        隠蔽状態かどうかbool値で返す。
        """
        return self.reversed

    def is_vanished(self):
        return self._vanished

    def has_beast(self):
        """
        付帯召喚じゃない召喚獣カードの所持数を返す。
        """
        return len([h for h in self.get_pocketcards(cw.POCKET_BEAST) if not h.attachment])

    def is_enhanced_act(self):
        return self.enhance_act <> 0 and 0 < self.enhance_act_dur

    def is_enhanced_res(self):
        return self.enhance_res <> 0 and 0 < self.enhance_res_dur

    def is_enhanced_avo(self):
        return self.enhance_avo <> 0 and 0 < self.enhance_avo_dur

    def is_enhanced_def(self):
        return self.enhance_def <> 0 and 0 < self.enhance_def_dur

    def is_upaction(self):
        return self.enhance_act > 0 and 0 < self.enhance_act_dur

    def is_upresist(self):
        return self.enhance_res > 0 and 0 < self.enhance_res_dur

    def is_upavoid(self):
        return self.enhance_avo > 0 and 0 < self.enhance_avo_dur

    def is_updefense(self):
        return self.enhance_def > 0 and 0 < self.enhance_def_dur

    def is_downaction(self):
        return self.enhance_act < 0 and 0 < self.enhance_act_dur

    def is_downresist(self):
        return self.enhance_res < 0 and 0 < self.enhance_res_dur

    def is_downavoid(self):
        return self.enhance_avo < 0 and 0 < self.enhance_avo_dur

    def is_downdefense(self):
        return self.enhance_def < 0 and 0 < self.enhance_def_dur

    def is_effective(self, motion):
        """motionが現在のselfに対して有効な効果か。
        ターゲットの選択に使用される判定であるため、
        実際には有効であっても必ずしもTrueを返さない。
        """
        if self.is_reversed() or self.is_vanished() or (self.status == "hidden" and not isinstance(self, (Friend, Player))):
            return False

        if cw.effectmotion.is_noeffect(motion.get("element", ""), self):
            return False

        mtype = motion.get("type", "")
        if mtype == "Heal":
            return self.is_injuredall()
        elif mtype == "Damage":
            return not self.is_unconscious()
        elif mtype == "Absorb":
            return not self.is_unconscious()
        elif mtype == "Paralyze":
            return not self.is_unconscious()
        elif mtype == "DisParalyze":
            return self.is_paralyze()
        elif mtype == "Poison":
            return not self.is_unconscious()
        elif mtype == "DisPoison":
            return self.is_poison()
        elif mtype == "GetSkillPower":
            return not self.is_unconscious()
        elif mtype == "LoseSkillPower":
            return not self.is_unconscious()
        elif mtype in "Sleep":
            # CardWirthでは、すでに睡眠状態なら
            # さらに大きな時間で上書き可能な状態でも
            # ターゲットにしない。
            # 混乱・激昂・勇敢・恐慌・呪縛・沈黙
            # ・暴露・魔法無効も同様
            return not self.is_unconscious() and not self.is_sleep()
        elif mtype == "Confuse":
            return not self.is_unconscious() and not self.is_confuse()
        elif mtype == "Overheat":
            return not self.is_unconscious() and not self.is_overheat()
        elif mtype == "Brave":
            return not self.is_unconscious() and not self.is_brave()
        elif mtype == "Panic":
            return not self.is_unconscious() and not self.is_panic()
        elif mtype == "Normal":
            return not self.is_unconscious() and not self.is_normal()
        elif mtype == "Bind":
            return not self.is_unconscious() and not self.is_bind()
        elif mtype == "DisBind":
            return self.is_bind()
        elif mtype == "Silence":
            return not self.is_unconscious() and not self.is_silence()
        elif mtype == "DisSilence":
            return self.is_silence()
        elif mtype == "FaceUp":
            return not self.is_unconscious() and not self.is_faceup()
        elif mtype == "FaceDown":
            return self.is_faceup()
        elif mtype == "AntiMagic":
            return not self.is_unconscious() and not self.is_antimagic()
        elif mtype == "DisAntiMagic":
            return self.is_antimagic()
        elif mtype == "EnhanceAction":
            # 能力ボーナスは時間を見ず、値のみを見て判定する
            if self.is_unconscious():
                return False
            value = motion.getint(".", "value", 0)
            if value == 0:
                return self.is_enhanced_act()
            elif value < 0:
                return value < self.get_enhance_act()
            elif 0 < value:
                return self.get_enhance_act() < value
        elif mtype == "EnhanceAvoid":
            if self.is_unconscious():
                return False
            value = motion.getint(".", "value", 0)
            if value == 0:
                return self.is_enhanced_avo()
            elif value < 0:
                return value < self.get_enhance_avo()
            elif 0 < value:
                return self.get_enhance_avo() < value
        elif mtype == "EnhanceResist":
            if self.is_unconscious():
                return False
            value = motion.getint(".", "value", 0)
            if value == 0:
                return self.is_enhanced_res()
            elif value < 0:
                return value < self.get_enhance_res()
            elif 0 < value:
                return self.get_enhance_res() < value
        elif mtype == "EnhanceDefense":
            if self.is_unconscious():
                return False
            value = motion.getint(".", "value", 0)
            if value == 0:
                return self.is_enhanced_def()
            elif value < 0:
                return value < self.get_enhance_def()
            elif 0 < value:
                return self.get_enhance_def() < value
        elif mtype == "VanishCard":
            return self.is_active()
        elif mtype == "VanishBeast":
            return self.has_beast()
        elif mtype == "DealAttackCard":
            return self.is_active()
        elif mtype == "DealPowerfulAttackCard":
            return self.is_active()
        elif mtype == "DealCriticalAttackCard":
            return self.is_active()
        elif mtype == "DealFeintCard":
            return self.is_active()
        elif mtype == "DealDefenseCard":
            return self.is_active()
        elif mtype == "DealDistanceCard":
            return self.is_active()
        elif mtype == "DealConfuseCard":
            return self.is_active()
        elif mtype == "DealSkillCard":
            return self.is_active()
        elif mtype == "CancelAction": # 1.50
            return self.is_active()
        elif mtype == "SummonBeast":
            return self.can_addbeast()
        elif mtype == "NoEffect": # Wsn.2
            return not self.is_unconscious()
        else:
            # VanishTarget: 常に有効
            return True

    #---------------------------------------------------------------------------
    #　カード操作
    #---------------------------------------------------------------------------

    def use_card(self, targets, header):
        """targetsにカードを使用する。"""
        cw.cwpy.advlog.use_card(self, header, targets)

        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if not isinstance(targets, list):
            targets = [targets]

        data = header.carddata
        # 他の使用中カード削除
        cw.cwpy.clear_inusecardimg()
        # TargetArrow削除
        cw.cwpy.clear_targetarrow()
        # 効果音ファイルのパスを取得
        soundpath = data.gettext("Property/SoundPath", "")
        volume = data.getint("Property/SoundPath", "volume", 100)
        loopcount = data.getint("Property/SoundPath", "loopcount", 1)
        channel = data.getint("Property/SoundPath", "channel", 0)
        fade = data.getint("Property/SoundPath", "fadein", 0)

        # 使用アニメーション
        cw.cwpy.event.in_inusecardevent = True
        removeafter = False
        battlespeed = cw.cwpy.is_battlestatus()
        if header.type == "BeastCard":
            cw.cwpy.set_inusecardimg(self, header, "hidden", center=True)
            inusecardimg = cw.cwpy.get_inusecardimg()
            cw.animation.animate_sprite(inusecardimg, "deal", battlespeed=battlespeed)
            # 効果音を鳴らす
            cw.cwpy.play_sound_with(soundpath, header, subvolume=volume, loopcount=loopcount, channel=channel, fade=fade)

            if cw.cwpy.setting.enlarge_beastcardzoomingratio:
                cw.animation.animate_sprite(inusecardimg, "zoomin_slow", battlespeed=battlespeed)
            else:
                inusecardimg.zoomsize_noscale = (16, 22)
                cw.animation.animate_sprite(inusecardimg, "zoomin", battlespeed=battlespeed)

            if cw.cwpy.setting.wait_usecard:
                waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())*2+1
                cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
            else:
                waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())+1
                cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)

            if cw.cwpy.setting.enlarge_beastcardzoomingratio:
                cw.animation.animate_sprite(inusecardimg, "zoomout_slow", battlespeed=battlespeed)
            else:
                cw.animation.animate_sprite(inusecardimg, "zoomout", battlespeed=battlespeed)

            cw.animation.animate_sprite(inusecardimg, "hide", battlespeed=battlespeed)
        elif isinstance(self, cw.character.Friend):
            self.set_pos_noscale(center_noscale=(316, 142))
            # NPC表示
            cw.cwpy.cardgrp.add(self, layer=self.layer)
            cw.animation.animate_sprite(self, "deal", battlespeed=battlespeed)
            # 表示中に効果音を鳴らす
            cw.cwpy.play_sound_with(soundpath, header, subvolume=volume, loopcount=loopcount, channel=channel, fade=fade)
            cw.animation.animate_sprite(self, "zoomin", battlespeed=battlespeed)
            # カード表示
            inusecardimg = cw.cwpy.set_inusecardimg(self, header, center=True)
            cw.cwpy.draw(clip=inusecardimg.rect)
            if cw.cwpy.setting.wait_usecard:
                waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())*2+1
                cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
            else:
                waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())+1
                cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)
            # カード消去
            cw.cwpy.clear_inusecardimg(self)
            # 自分が対象の時でなければNPC消去
            if not self in targets:
                cw.animation.animate_sprite(self, "zoomout", battlespeed=battlespeed)
                cw.animation.animate_sprite(self, "hide", battlespeed=battlespeed)
                cw.cwpy.cardgrp.remove(self)
            else:
                removeafter = True
        else:
            cw.cwpy.set_inusecardimg(self, header)
            # 効果音を鳴らす
            cw.cwpy.play_sound_with(soundpath, header, subvolume=volume, loopcount=loopcount, channel=channel, fade=fade)
            cw.animation.animate_sprite(self, "zoomin", battlespeed=battlespeed)
            if cw.cwpy.setting.wait_usecard:
                waitrate = cw.cwpy.setting.get_dealspeed(cw.cwpy.is_battlestatus())
                cw.cwpy.wait_frame(waitrate, cw.cwpy.setting.can_skipanimation)

        # 宿へ取り込んだ特殊文字の使用時イベントでの表示に備える
        specialchars = cw.cwpy.rsrc.specialchars
        specialchars_is_changed = cw.cwpy.rsrc.specialchars_is_changed
        e_mates = header.carddata.find("Property/Materials")
        can_loaded_scaledimage = header.carddata.getbool(".", "scaledimage", False)
        if cw.cwpy.is_playingscenario() and not e_mates is None:
            specialchars = specialchars.copy()
            dpath = cw.util.join_yadodir(e_mates.text)
            if os.path.isdir(dpath):
                for fname in os.listdir(dpath):
                    cw.cwpy.sdata.eat_spchar(dpath, fname, can_loaded_scaledimage)

        try:
            # カードイベント開始
            e = data.find("Events/Event")
            cw.event.CardEvent(e, header, self, targets).start()
        finally:
            if removeafter:
                # NPC消去
                battlespeed = cw.cwpy.is_battlestatus()
                cw.animation.animate_sprite(self, "hide", battlespeed=battlespeed)
                cw.cwpy.cardgrp.remove(self)
            # 特殊文字を元に戻す
            cw.cwpy.rsrc.specialchars = specialchars
            cw.cwpy.rsrc.specialchars_is_changed = specialchars_is_changed

    def throwaway_card(self, header, from_event=True, update_image=True):
        """
        引数のheaderのカードを破棄処理する。
        """
        if cw.cwpy.ydata:
            cw.cwpy.trade("TRASHBOX", header=header, from_event=from_event, update_image=update_image)
        else:
            if header.type == "SkillCard":
                index = 0
            elif header.type == "ItemCard" :
                index = 1
            elif header.type == "BeastCard":
                index = 2
            self.cardpocket[index].remove(header)

    #---------------------------------------------------------------------------
    #　戦闘行動関係
    #---------------------------------------------------------------------------

    def action(self):
        """設定している戦闘行動を行う。
        BattleEngineからのみ呼ばれる。
        """
        if self.actiondata:
            targets, header, beasts = self.actiondata

            # 召喚獣カードの使用
            if isinstance(self, cw.sprite.card.FriendCard):
                ishidden = self._vanished
            else:
                ishidden = self.status == "hidden"

            if self.is_alive() and not ishidden and self.status <> "reversed":
                for targets_b, header_b in beasts[:]:
                    inarr = False
                    for _targets_c, header_c in self.actiondata[2]:
                        if header_c == header_b:
                            inarr = True
                            break
                    if not inarr:
                        # カードの効果で召喚獣カードが
                        # いなくなっている場合
                        continue

                    self.use_card(targets_b, header_b)

                    # 戦闘勝利チェック
                    if cw.cwpy.is_battlestatus() and cw.cwpy.battle.check_win():
                        raise cw.battle.BattleWinError()

                    if isinstance(self, cw.sprite.card.FriendCard):
                        ishidden = self._vanished
                    else:
                        ishidden = self.status == "hidden"

                    # カードの効果で行動が変わっている可能性がある
                    if not self.actiondata or ishidden or self.status == "reversed" or not cw.cwpy.is_battlestatus():
                        break

            # 手札カードの使用
            if self.is_alive() and not ishidden and self.status <> "reversed" and self.actiondata and cw.cwpy.is_battlestatus():
                targets, header, beasts = self.actiondata
                if header and self.is_active() and not ishidden and self.status <> "reversed":
                    self.deck.use(header)
                    self.use_card(targets, header)

    def set_action(self, target, header, beasts=[][:], auto=False):
        """
        戦闘行動を設定。
        auto: 自動手札選択から設定されたかどうか。
        """
        if auto:
            self.clear_action()
            self.actiondata = (target, header, beasts)
            self.actionautoselected = auto
        else:
            if self.actiondata:
                beasts = self.actiondata[2]

            self.clear_action()
            self.actiondata = (target, header, beasts)
            self.actionautoselected = auto
            cw.cwpy.play_sound("page")
            assert cw.cwpy.pre_dialogs, "%s, %s" % (self.name, header.name)
            if cw.cwpy.pre_dialogs:
                cw.cwpy.pre_dialogs.pop()

        if cw.cwpy.battle and target and header:
            # 召喚獣は個々の選択時に優先行動済みリストへ追加される
            self._add_priorityacts(target, header)

        self.actionend = False

    def _add_priorityacts(self, target, h):
        if cw.cwpy.battle and target and h:
            for e in self._get_motions(h):
                t = e.get("type", "")
                if not self._is_bonusedmtype(t):
                    continue
                if t:
                    cw.cwpy.battle.priorityacts.append((t, target, self))

    def adjust_action(self):
        """
        現在の状態に合わせて一部戦闘行動を解除する。
        行動不能であれば自律的な行動は行えず、
        麻痺・死亡状態であれば召喚獣も動けない。
        """
        if self.actiondata:
            if self.is_unconscious():
                self.clear_action()
            elif self.is_inactive(check_reversed=False):
                _target, _header, beasts = self.actiondata
                self.set_action(None, None, beasts, True)

        if self.is_inactive(check_reversed=False):
            self.deck.throwaway()

    def clear_action(self):
        self.actiondata = None
        self.actionautoselected = False
        self.actionend = True
        if cw.cwpy.battle:
            for key, target, user in cw.cwpy.battle.priorityacts[:]:
                if user == self:
                    cw.cwpy.battle.priorityacts.remove((key, target, user))

    def is_autoselectedpenalty(self, header=None):
        """戦闘中にペナルティカードを自動選択した状態か。
        headerにNone以外が指定された時は、選択されたペナルティカードが
        指定されたheaderと一致する時のみTrueを返す。
        """
        if cw.cwpy.battle and self.actiondata and self.actionautoselected:
            headerp = self.actiondata[1]
            return headerp and headerp.penalty and (header is None or header == headerp)
        return False

    #---------------------------------------------------------------------------
    #　判定用
    #---------------------------------------------------------------------------

    def decide_outcome(self, level, vocation, thresholdbonus=6, enhance=0, subbonus=0):
        """
        行為判定を行う。成功ならTrue。失敗ならFalseを返す。
        level: 判定レベル。
        vocation: 適性データ。(身体適性名, 精神適性名)のタプル。
        thresholdbonus: アクション元の適性値+行動力強化値。効果コンテントだと6。
        enhance: 回避・抵抗判定の場合はボーナス値。
        subbonus: 各種判定のサブボーナス(現在は成功率修正のみ)。
        """
        dice = cw.cwpy.dice.roll(2)
        if dice == 12:
            return True
        elif dice == 2:
            return False

        udice = cw.cwpy.dice.roll(2)
        tdice = dice

        thresholdbonus = int(thresholdbonus)
        voc = self.get_vocation_val(vocation)
        bonus = int(voc + enhance)
        uvalue = cw.util.div_vocation(thresholdbonus) + level + subbonus + udice
        tvalue = cw.util.div_vocation(bonus) + self.level + tdice
        return uvalue <= tvalue

    def decide_misfire(self, level):
        """
        カードの不発判定を行う。成功ならTrue。失敗ならFalseを返す。
        level: 判定レベル(カードの技能レベル)。
        """
        dice = cw.cwpy.dice.roll(2)
        threshold = level - self.level - 1

        if dice == 12:
            flag = True
        elif dice >= threshold:
            flag = True
        else:
            flag = False

        return flag

    #---------------------------------------------------------------------------
    #　戦闘行動設定関連
    #---------------------------------------------------------------------------

    def decide_actionorder(self):
        """
        行動順位を判定する数値をself.actionorderに設定。
        敏捷度と大胆性で判定。レベル・行動力は関係なし。
        FIXME: これによって決定される行動順はCardWirthと若干異なる
        """
        vocation_val = int(self.get_vocation_val(("agl", "uncautious")))
        d = cw.cwpy.dice.roll(2, 6)
        self.actionorder = int((vocation_val+1) * 1.4) + d
        return self.actionorder

    def decide_action(self):
        """
        自動手札選択。
        """
        self.clear_action()
        if self.is_dead() or not cw.cwpy.status == "ScenarioBattle":
            return

        # 召喚獣カード
        beasts = []

        for header in self.get_pocketcards(cw.POCKET_BEAST):
            if header.is_autoselectable():
                targets, effectivetargets = header.get_targets()

                if effectivetargets:
                    # 優先度の高いターゲットが存在する場合はそちらを優先選択する
                    bonus, effectivetargets = self._get_targetingbonus_and_targets(header, effectivetargets)

                    if not header.allrange and len(targets) > 1:
                        targets = [cw.cwpy.dice.choice(effectivetargets)]

                    beasts.append((targets, header))
                    # 優先行動済みリストへ追加する
                    self._add_priorityacts(targets, header)

        # 行動不能時は召喚獣のみ
        if self.is_inactive():
            self.set_action(None, None, beasts, True)
            return

        # 使用するカード
        headers = []

        for header in self.deck.hand:
            if header.is_autoselectable():
                targets, effectivetargets = header.get_targets()

                if effectivetargets or header.target == "None":
                    if not header.allrange:
                        targets = effectivetargets

                    headers.append((targets, header))

        targets, header = self.decide_usecard(headers)

        if header and not header.allrange and len(targets) > 1:
            targets = [cw.cwpy.dice.choice(targets)]

        # 行動設定
        self.set_action(targets, header, beasts, True)

    def decide_usecard(self, headers):
        """
        使用可能な手札のいずれかを自動選択する。
        """
        # 手札交換は次の特殊処理を行う
        #  * 常に最後に判定する
        #  * 適性値を-6する
        seq = [] # 手札交換以外のカード
        exchange = [] # 手札交換
        for t in headers:
            header = t[1]
            if header.type == "ActionCard" and header.id == 0:
                exchange.append(t)
            else:
                seq.append(t)
        assert len(seq)+len(exchange) == len(headers)

        # カードを選択する(手札交換以外)

        # 選択値
        # カードごとに決定し、これまでの最大値を上回れば選択
        maxd = -2147483647
        # 選択されたカード
        selected = (None, None)
        for i, t in enumerate(itertools.chain(seq, exchange)):
            header = t[1]

            # 適性値
            vocation = int(header.get_vocation_val(self))
            if len(seq) <= i:
                vocation -= 6 # 手札交換なので-6
            else:
                vocation = max(0, vocation)

            # 優先選択ボーナス
            bonus, targs = self._get_targetingbonus_and_targets(header, t[0])

            # 選択値を計算
            d = cw.cwpy.dice.roll()
            d = (1 + vocation) // 2 + d + bonus
            if maxd < d:
                # 選択する
                selected = (targs, header)
                maxd = d

        return selected

    def _get_motions(self, header):
        if header.type == "ActionCard" and header.id == 7:
            # 逃走の場合は"VanishTarget"を"Runaway"というボーナス判定用特殊効果に置換する
            return [{"type":"Runaway"}]
        else:
            return header.carddata.getfind("Motions").getchildren()

    def _is_bonusedmtype(self, mtype):
        return mtype in ("Runaway", "Heal")

    def _get_targetingbonus_and_targets(self, header, targets):
        bonus = -2147483647
        maxbonustargs = []
        # 最大ボーナスを取得
        motions = self._get_motions(header)
        for motion in motions:
            mtype = motion.get("type", "")
            if not self._is_bonusedmtype(mtype):
                continue
            for targ in targets:
                b = targ.get_targetingbonus(mtype)
                if bonus == b:
                    maxbonustargs.append(targ)
                elif bonus < b:
                    maxbonustargs = [targ]
                    bonus = b

        if bonus == -2147483647:
            return 0, targets
        return bonus, targets if header.allrange else maxbonustargs

    #---------------------------------------------------------------------------
    #　状態取得用
    #---------------------------------------------------------------------------

    def get_targetingbonus(self, mtype):
        """
        効果のターゲットとして選ばれやすくなるボーナス値を返す。
        現在は"Heal"タイプに対する体力減時ボーナスと
        "Runaway"(逃走効果に対する特殊タイプ)に対する重傷時ボーナスのみ。
        mtype: 効果タイプ。
        """
        bonus = 0
        if mtype == "Heal":
            per = self.get_lifeper()
            if 50 <= per:
                bonus = -1
            elif 33 <= per:
                bonus = 0
            elif 25 <= per:
                bonus = 1
            elif 20 <= per:
                bonus = 2
            elif 16 <= per:
                bonus = 3
            elif 14 <= per:
                bonus = 4
            elif 12 <= per:
                bonus = 5
            elif 1 <= per:
                bonus = 6 + (11 - per)
            else:
                bonus = 100

        elif mtype == "Runaway":
            per = self.get_lifeper()
            if 50 <= per:
                bonus = 3
            elif 33 <= per:
                bonus = 4
            elif 25 <= per:
                bonus = 5
            elif 20 <= per:
                bonus = 6
            elif 16 <= per:
                bonus = 7
            elif 14 <= per:
                bonus = 8
            elif 12 <= per:
                bonus = 9
            else:
                bonus = 10 + (11 - per)

        if cw.cwpy.battle:
            # すでにその行動のターゲットになっている場合はボーナスを入れず、
            # ターゲット回数分をペナルティとする(選択されにくくなる)
            targeting = 0
            for s, tarr, _user in cw.cwpy.battle.priorityacts:
                if mtype == s:
                    if isinstance(tarr, cw.character.Character):
                        if tarr == self:
                            targeting += 1
                    elif self in tarr:
                        targeting += 1
            if targeting:
                bonus = min(0, bonus)
                if mtype == "Heal":
                    bonus -= targeting

        return bonus

    def get_pocketcards(self, index):
        """
        所持しているカードを返す。
        index: カードの種類。
        """
        return self.cardpocket[index]

    def get_cardpocketspace(self):
        """
        最大所持カード枚数を
        (スキルカード, アイテムカード, 召喚獣カード)のタプルで返す
        """
        maxskillnum = self.level / 2 + self.level % 2 + 2
        maxskillnum = cw.util.numwrap(maxskillnum, 1, 10)
        maxbeastnum = (self.level + 2) / 4

        if (self.level + 2) % 4:
            maxbeastnum += 1

        maxbeastnum = cw.util.numwrap(maxbeastnum, 1, 10)
        return (maxskillnum, maxskillnum, maxbeastnum)

    @staticmethod
    def calc_lifeper(life, maxlife):
        return int(100.0 * life // maxlife + 0.5)

    def get_lifeper(self):
        """
        ライフのパーセンテージを返す。
        """
        return Character.calc_lifeper(self.life, self.maxlife)

    def get_bonus(self, vocation, enhance_act=True):
        """
        適性値と行動力強化値を合計した、行為判定用のボーナス値を返す。
        vocation: 適性データ。(身体適性名, 精神適性名)のタプル。
        enhance_act: 行動力修正の影響を受けるか。
        """
        value = self.get_vocation_val(vocation)
        if enhance_act:
            value += self.get_enhance_act()
        return value

    def get_vocation_val(self, vocation):
        """
        適性値(身体適性値 + 精神適性値)を返す。
        引数のvocationは(身体適性名, 精神適性名)のタプル。
        """
        vo = vocation
        voc = self._voc_tbl.get(vo, None)
        if not voc is None:
            return voc
        vocation = (vocation[0].lower(), vocation[1].lower())
        physical = vocation[0]
        mental = vocation[1].replace("un", "", 1)
        physical = self.physical.get(physical)
        mental = self.mental.get(mental)

        if vocation[1].find("un") > -1:
            mental = -mental

        if int(mental) <> mental:
            if mental < 0:
                mental += 0.5
            else:
                mental -= 0.5
            mental = int(mental)

        voc = int(physical + mental)
        voc = cw.util.numwrap(voc, -65536, 65536)
        self._voc_tbl[vo] = voc
        return voc

    def _clear_vocationcache(self):
        """能力値のキャッシュをクリアする。"""
        self._voc_tbl = {}

    def get_enhance_act(self):
        """
        行動力強化値を返す。行動力は効果コンテントによる強化値だけ。
        """
        return cw.util.numwrap(self.enhance_act, -10, 10)

    def get_enhance_def(self):
        """
        初期・状態・カードによる防御力修正の計算結果を返す。
        単体で+10の修正がない場合は、合計値が+10を越えていても+9を返す。
        """
        return self._get_enhance_impl("defense", self.enhance_def, 2)

    def get_enhance_res(self):
        """
        初期・状態・カードによる抵抗力修正の計算結果を返す。
        """
        return self._get_enhance_impl("resist", self.enhance_res, 1)

    def get_enhance_avo(self):
        """
        初期・状態・カードによる回避力修正の計算結果を返す。
        """
        return self._get_enhance_impl("avoid", self.enhance_avo, 0)

    def _calc_enhancevalue(self, header, value):
        """使用・所持ボーナス値に適性による補正を加える。
        BUG: CardWirthではアイテムの所持ボーナスに限り
              最低適性(level=0)の時に補正係数が50%となるが、
             それ以外の全てのパターンではそのような計算が
             行われないため、バグと思われる
        """
        if value <= 0:
            return value
        level = header.get_vocation_level(self, enhance_act=False)
        if level <= 2:
            value2 = cw.util.numwrap(value, -10, 10)
        else:
            value2 = cw.util.numwrap(value * 150 / 100, -10, 10)

        return value2

    def _get_enhance_impl(self, name, initvalue, enhindex):
        """
        現在かけられている全ての能力修正値の合計を返す(ただし単純な加算ではない)。
        デフォルト修正値 + 状態修正値 + カード所持修正値 + カード使用修正値。
        ただしカードの修正値は適性による補正を受ける。
        """
        val1 = int(self.enhance.get(name))
        val1 = cw.util.numwrap(val1, -10, 10)
        val2 = int(initvalue)
        val2 = cw.util.numwrap(val2, -10, 10)
        seq = [val1, val2]
        pvals = []
        def add_pval(val):
            if 0 < val and val < 10:
                pvals.append(int(val))

        def addval(header, val, using=False):
            if name == "defense":
                val = int(val)
                val2 = val
                if header.type == "SkillCard":
                    # 特殊技能使用
                    assert using
                    level = header.get_vocation_level(self, enhance_act=False)
                    if 2 <= level:
                        val = val * 120 // 100
                    add_pval(val)
                    val = val2
                elif header.type == "ItemCard" and using:
                    # アイテム使用
                    add_pval(val)
                elif header.type == "ItemCard":
                    # アイテム所持
                    level = header.get_vocation_level(self, enhance_act=False)
                    if val < 0:
                        if 3 <= level:
                            val = val * 80 // 100
                        elif level <= 0:
                            val = val * 150 // 100
                        add_pval(val)
                    elif 0 < val:
                        if level <= 0:
                            val = val * 50 // 100
                        elif level <= 1:
                            val = val * 80 // 100
                        add_pval(val)
                elif header.type == "BeastCard":
                    # 召喚獣所持
                    add_pval(val)
                else:
                    assert header.type == "ActionCard"
                    add_pval(val)
            else:
                val = self._calc_enhancevalue(header, val)
                add_pval(val)
            val = int(val)
            seq.append(val)

        if self.actiondata and self.actiondata[1]:
            header = self.actiondata[1]
        elif self.deck and self.deck.get_used():
            header = self.deck.get_used()
        else:
            header = None

        if header:
            val4 = header.get_enhance_val_used()[enhindex]
            addval(header, val4, True)

        for header in itertools.chain(self.get_pocketcards(cw.POCKET_BEAST),
                                      self.get_pocketcards(cw.POCKET_ITEM)):
            val3 = header.get_enhance_val()[enhindex]
            addval(header, val3)

        add_pval(val1)
        add_pval(val2)

        a = 0
        b = 0
        ac = 0
        bc = 0
        max10 = 0
        max10counter = 0
        maxval = 0
        minval = 0
        for val in seq:
            if val < 0:
                if a == 0:
                    a = (10 + val)
                else:
                    a *= (10 + val)
                ac += 1
                minval = min(minval, val)
                max10counter += -val//6 + 1
            elif 0 < val:
                if b == 0:
                    b = (10 - val)
                else:
                    b *= (10 - val)
                bc += 1
                max10 += val // 10
                maxval = max(maxval, val)
        if ac:
            a /= math.pow(10, ac-1)
            a = 10 - a
            a = max(-minval, a)
        if bc:
            b /= math.pow(10, bc-1)
            b = 10 - b
            b = max(maxval, b)

        pvalr = 100
        for pval in reversed(pvals):
            pvalr *= 10
            pvalr *= 10-pval
            pvalr //= 100

        if pvalr < 1:
            # 防御修正でn[1],n[2],n[3],...,n[N]の値がある時、
            # (1-n[N]/10)*(1-n[N-1]/10)*...,(1-n[1]/10)の結果が
            # 0.01未満になれば+10効果を得られる(計算途中の誤差は切り捨て)。
            # ただし適性による変動がある
            max10 += 1

        if max10 < 3:
            # 防御修正で+10があると完全にダメージが無くなるが、
            # -1～5で1回、-6以上で2回分、+10効果を打ち消すことができる
            # ただし+30以上は無効化不可
            max10 -= max10counter

        value = int(b) - int(a)
        if name == "defense":
            if 0 < max10:
                value = 10
            else:
                # 防御ボーナスは単体の+10がない限り最大で+9になる
                value = cw.util.numwrap(value, -10, 9)
        else:
            value = cw.util.numwrap(value, -10, 10)

        return value

    #---------------------------------------------------------------------------
    #　クーポン関連
    #---------------------------------------------------------------------------

    @synclock(_couponlock)
    def get_coupons(self):
        """
        所有クーポンをセット型で返す。
        """
        return self._get_coupons()
    def _get_coupons(self):
        return set(self.coupons.iterkeys())

    @synclock(_couponlock)
    def get_couponvalue(self, name, raiseerror=True):
        """
        クーポンの値を返す。
        """
        return self._get_couponvalue(name, raiseerror)

    def _get_couponvalue(self, name, raiseerror=True):
        if raiseerror:
            return self.coupons[name][0]
        else:
            data = self.coupons.get(name, None)
            if data:
                return data[0]
            else:
                return None

    @synclock(_couponlock)
    def has_coupon(self, coupon):
        """
        引数のクーポンを所持しているかbool値で返す。
        """
        return self._has_coupon(coupon)

    def _has_coupon(self, coupon):
        return coupon in self.coupons

    @synclock(_couponlock)
    def get_couponsvalue(self):
        return self._get_couponsvalue()

    def _get_couponsvalue(self):
        """
        全ての所持クーポンの点数を合計した値を返す。
        """
        cnt = 0

        for coupon, data in self.coupons.iteritems():
            if coupon and not coupon[0] in (u"＠", u"：", u"；"):
                value = data[0]
                cnt += value

        return cnt

    @synclock(_couponlock)
    def get_specialcoupons(self):
        """
        "＠"で始まる特殊クーポンの
        辞書(key=クーポン名, value=クーポン得点)を返す。
        """
        return self._get_specialcoupons()

    def _get_specialcoupons(self):
        d = {}

        for coupon, data in self.coupons.iteritems():
            if coupon and coupon.startswith(u"＠"):
                value = data[0]
                d[coupon] = value

        return d

    @synclock(_couponlock)
    def replace_allcoupons(self, seq, syscoupons={}.copy()):
        """システムクーポン以外の全てのクーポンを
        listの内容に入れ替える。
        所持クーポンが変化したらTrueを返す。
        seq: クーポン情報のタプル(name, value)のリスト。
        syscoupons: このコレクション内にあるクーポンは
                    システムクーポンとして処理対象外にする
        """
        old_coupons = {}
        for name, (value, e) in self.coupons.iteritems():
            old_coupons[name] = value
        revcoupon_old = False
        revcoupon_new = False
        # システムクーポン以外を一旦除去
        for name in self._get_coupons():
            if syscoupons is None or not (name.startswith(u"＠") or name in syscoupons):
                self._remove_coupon(name, False)
            revcoupon_old |= (name == u"：Ｒ")

        sexcoupons = set(cw.cwpy.setting.sexcoupons)
        periodcoupons = set(cw.cwpy.setting.periodcoupons)
        naturecoupons = set(cw.cwpy.setting.naturecoupons)

        # クーポン追加
        for coupon in seq:
            name = coupon[0]
            if name in sexcoupons:
                old = self._get_sex()
                if old:
                    self._remove_coupon(old)
            if name in periodcoupons:
                old = self._get_age()
                if old:
                    self._remove_coupon(old)
            if name in naturecoupons:
                old = self._get_talent()
                if old:
                    self._remove_coupon(old)

            self._set_coupon(name, coupon[1], False)
            revcoupon_new |= (name == u"：Ｒ")

        # 隠蔽クーポン
        if revcoupon_old <> revcoupon_new:
            self.reversed = revcoupon_old
            if self.status == "hidden":
                self.reverse()
            else:
                cw.animation.animate_sprite(self, "reverse")

        new_coupons = {}
        for name, (value, e) in self.coupons.iteritems():
            new_coupons[name] = value
        return new_coupons <> old_coupons

    @synclock(_couponlock)
    def get_sex(self):
        return self._get_sex()

    def _get_sex(self):
        for coupon in cw.cwpy.setting.sexcoupons:
            if coupon in self.coupons:
                return coupon

        return cw.cwpy.setting.sexcoupons[0]

    @synclock(_couponlock)
    def set_sex(self, sex):
        self._set_sex(sex)

    def _set_sex(self, sex):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        old = self._get_sex()
        if old:
            self._remove_coupon(old)
        self._set_coupon(sex, 0)

    @synclock(_couponlock)
    def has_sex(self):
        return self._has_sex()

    def _has_sex(self):
        for coupon in cw.cwpy.setting.sexcoupons:
            if coupon in self.coupons:
                return True

        return False

    @synclock(_couponlock)
    def get_age(self):
        return self._get_age()

    def _get_age(self):
        for coupon in cw.cwpy.setting.periodcoupons:
            if coupon in self.coupons:
                return coupon

        return cw.cwpy.setting.periodcoupons[0]

    @synclock(_couponlock)
    def set_age(self, age):
        self._set_age(age)

    def _set_age(self, age):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        old = self._get_age()
        if old:
            self._remove_coupon(old)
        self._set_coupon(age, 0)

    @synclock(_couponlock)
    def has_age(self):
        return self._has_age()

    def _has_age(self):
        for coupon in cw.cwpy.setting.periodcoupons:
            if coupon in self.coupons:
                return True

        return False

    @synclock(_couponlock)
    def get_talent(self):
        return self._get_talent()

    def _get_talent(self):
        for coupon in cw.cwpy.setting.naturecoupons:
            if coupon in self.coupons:
                return coupon

        return cw.cwpy.setting.naturecoupons[0]

    @synclock(_couponlock)
    def set_talent(self, talent):
        self._set_talent(talent)

    def _set_talent(self, talent):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        old = self._get_talent()
        if old:
            self._remove_coupon(old)
        self._set_coupon(talent, 0)

    @synclock(_couponlock)
    def has_talent(self):
        return self._has_talent()

    def _has_talent(self):
        for coupon in cw.cwpy.setting.naturecoupons:
            if coupon in self.coupons:
                return True

        return False

    @synclock(_couponlock)
    def get_makings(self):
        return self._get_makings()

    def _get_makings(self):
        """
        所持する特徴クーポンをセット型で返す。
        """
        makings = set()
        for making in cw.cwpy.setting.makingcoupons:
            if making in self.coupons:
                makings.add(making)
        return makings

    @synclock(_couponlock)
    def set_makings(self, makings):
        return self._set_makings(makings)

    def _set_makings(self, makings):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        for coupon in cw.cwpy.setting.makingcoupons:
            if coupon in self.coupons:
                self._remove_coupon(coupon)
        for coupon in makings:
            self._set_coupon(coupon, 0)

    @synclock(_couponlock)
    def set_race(self, race):
        self._set_race(race)
    def _set_race(self, race):
        old = self._get_race()
        if race == old:
            return
        if not isinstance(old, cw.header.UnknownRaceHeader):
            self._remove_coupon(u"＠Ｒ" + old.name)
        if not isinstance(race, cw.header.UnknownRaceHeader):
            self._set_coupon(u"＠Ｒ" + race.name, 0)

    @synclock(_couponlock)
    def get_race(self):
        return self._get_race()

    def _get_race(self):
        for race in cw.cwpy.setting.races:
            if self._has_coupon(u"＠Ｒ" + race.name):
                return race
        return cw.cwpy.setting.unknown_race

    @synclock(_couponlock)
    def count_timedcoupon(self, value=-1):
        """
        時限クーポンの点数を減らす。
        value: 減らす数。
        """
        if self.timedcoupons:
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self.data.is_edited = True

            for coupon in list(self.timedcoupons):
                oldvalue, e = self.coupons[coupon]
                if oldvalue == 0:
                    continue

                n = oldvalue + value
                n = cw.util.numwrap(n, 0, 999)

                if n > 0:
                    e.set("value", str(n))
                    self.coupons[coupon] = n, e
                else:
                    self._remove_coupon(coupon)

    @synclock(_couponlock)
    def set_coupon(self, name, value):
        """
        クーポンを付与する。同名のクーポンがあったら上書き。
        時限クーポン("："or"；"で始まるクーポン)はtimedcouponsに登録する。
        name: クーポン名。
        value: クーポン点数。
        """
        self._set_coupon(name, value, True)

    def _set_coupon(self, name, value, update=True):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        value = int(value)
        value = cw.util.numwrap(value, -999, 999)
        removed = self._remove_coupon(name, False)
        e = self.data.make_element("Coupon", name, {"value" : str(value)})
        self.data.append("Property/Coupons", e)
        self.coupons[name] = value, e

        # 時限クーポン
        if name.startswith(u"：") or name.startswith(u"；"):
            self.timedcoupons.add(name)

        # 隠蔽クーポン
        if name == u"：Ｒ" and not self.is_reversed():
            if update and not removed:
                if self.status == "hidden":
                    self.reverse()
                else:
                    cw.animation.animate_sprite(self, "reverse")
            self.reversed = True

        if not removed:
            # 効果対象の変更(Wsn.2)
            effectevent = cw.cwpy.event.get_effectevent()
            if effectevent and name == u"＠効果対象":
                effectevent.add_target(self)

        # 隠蔽クーポンがあるため
        self.adjust_action()

    @synclock(_couponlock)
    def get_timedcoupons(self):
        """
        時限クーポンのデータをまとめたsetを返す。
        """
        s = set()

        for coupon in self.coupons.iterkeys():
            if coupon.startswith(u"：") or coupon.startswith(u"；"):
                s.add(coupon)

        return s

    @synclock(_couponlock)
    def remove_coupon(self, name):
        """
        同じ名前のクーポンを全て剥奪する。
        name: クーポン名。
        """
        return self._remove_coupon(name, True)

    def _remove_coupon(self, name, update=True):
        if not name in self.coupons:
            return False
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()

        _value, e = self.coupons[name]
        self.data.remove("Property/Coupons", e)
        del self.coupons[name]

        # 時限クーポン
        if name in self.timedcoupons:
            self.timedcoupons.remove(name)

        # 隠蔽クーポン
        if name == u"：Ｒ" and self.is_reversed():
            if update:
                if self.status == "hidden":
                    self.reverse()
                else:
                    cw.animation.animate_sprite(self, "reverse")
            self.reversed = False

        # 効果対象の変更(Wsn.2)
        effectevent = cw.cwpy.event.get_effectevent()
        if effectevent and name == u"＠効果対象":
            effectevent.remove_target(self)

        return True

    @synclock(_couponlock)
    def remove_timedcoupons(self, battleonly=False):
        """
        時限クーポンを削除する。イメージは更新しない。
        battleonly: Trueの場合は"；"の時限クーポンのみ削除。
        """
        for name in set(self.timedcoupons):
            if not battleonly or name.startswith(u"；"):
                self._remove_coupon(name, False)

    @synclock(_couponlock)
    def remove_numbercoupon(self):
        """
        "＿１"等の番号クーポンを削除。
        """
        # u"＠ＭＰ３"はCardWirth 1.29以降で配布されるクーポン
        names = [cw.cwpy.msgs["number_1_coupon"], u"＿１", u"＿２", u"＿３", u"＿４", u"＿５", u"＿６", u"＠ＭＰ３"]

        for name in names:
            self._remove_coupon(name)

    #---------------------------------------------------------------------------
    #　レベル変更用
    #---------------------------------------------------------------------------

    @synclock(_couponlock)
    def get_limitlevel(self):
        """レベルの調節範囲の最大値を返す。"""
        return self._get_limitlevel()

    def _get_limitlevel(self):
        l = self._get_couponvalue(u"＠レベル原点", raiseerror=False)
        if not l is None:
            return max(self.level, l)
        else:
            return self.level

    @synclock(_couponlock)
    def check_level(self):
        coupons = self._get_specialcoupons()
        level = coupons[u"＠レベル原点"]

        limit = self._get_levelmax(coupons)
        if not u"＠レベル上限" in coupons:
            self._set_coupon(u"＠レベル上限", limit)

        # 解の公式で現在の経験点で到達できるレベルを算出
        cnt = max(1, self._get_couponsvalue())
        olevel = int((-1 + math.sqrt(1 + 4 * cnt)) / 2.0) + 1
        olevel = min(limit, olevel)

        return olevel - level

    @synclock(_couponlock)
    def get_levelmax(self):
        coupons = self._get_specialcoupons()
        return self._get_levelmax(coupons)

    def _get_levelmax(self, coupons):
        if u"＠レベル上限" in coupons:
            limit = coupons[u"＠レベル上限"]
        elif u"＠本来の上限" in coupons:
            limit = coupons[u"＠本来の上限"]
            self._set_coupon(u"＠レベル上限", limit)
        else:
            limit = 10
        return limit

    @synclock(_couponlock)
    def set_level(self, value, regulate=False, debugedit=False, backpack_party=None, revert_cardpocket=True):
        """レベルを設定する。
        regulate: レベルを調節する場合はTrue。
        backpack_party: レベルが下がって手札を持ちきれなくなった際、
                        このパーティの荷物袋へ入れる。
                        Noneの場合はアクティブなパーティの荷物袋か
                        カード置場へ入る。
        """
        # 調節前のレベル
        limit = self._get_limitlevel()
        if regulate:
            value = min(value, limit)

        # レベル
        uplevel = value - self.level
        if uplevel == 0:
            return

        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()

        vit = max(1, int(self.physical.get("vit")))
        minval = max(1, int(self.physical.get("min")))

        coeff = self.data.getfloat("Property/Life", "coefficient", 0.0)
        if coeff <= 0.0:
            maxlife = calc_maxlife(vit, minval, self.level)
            if int(maxlife) == self.maxlife:
                coeff = 1
            else:
                # 最大HP10でレベル10のキャラクタのレベルを9に下げたら
                # 最大HPが90に増えてしまった、というような問題を
                # 避けるため、計算上の体力と実際の最大体力が食い違う
                # 場合は計算用係数を付与する
                coeff = float(self.maxlife) / int(maxlife)
                self.data.edit("Property/Life", str(coeff), "coefficient")

        self.level = value
        self.data.edit("Property/Level", str(self.level))
        # 最大HPとHP
        maxlife = calc_maxlife(vit, minval, self.level)
        if coeff <> 1:
            maxlife = round(maxlife * coeff)
        maxlife = int(max(1, maxlife))
        self.maxlife += maxlife - self.maxlife
        self.data.edit("Property/Life", str(self.maxlife), "max")
        self.set_life(self.maxlife)
        # 技能の使用回数
        for header in self.cardpocket[cw.POCKET_SKILL]:
            header.get_uselimit(reset=True)

        if not regulate:
            # レベル原点・EPクーポン操作
            for e in self.data.find("Property/Coupons"):
                if not e.text:
                    continue

                if e.text == u"＠レベル原点":
                    e.attrib["value"] = str(self.level)
                    self.coupons[e.text] = self.level, e
                elif e.text == u"＠ＥＰ":
                    value = e.getint(".", "value", 0) + (value - limit) * 10
                    e.attrib["value"] = str(value)
                    self.coupons[e.text] = value, e

        if uplevel < 0:
            # 所持可能上限を越えたカードを、荷物袋ないしカード置き場へ移動
            if backpack_party or isinstance(self, cw.sprite.card.PlayerCard):
                targettype = "BACKPACK"
            else:
                targettype = "STOREHOUSE"
            targettype_original = targettype
            for index in range(3):
                n = len(self.cardpocket[index])
                maxn = self.get_cardpocketspace()[index]
                while n > maxn:
                    header = self.cardpocket[index][-1]
                    if index == cw.POCKET_BEAST and not header.attachment:
                        targettype = "TRASHBOX"
                    else:
                        targettype = targettype_original
                    if regulate and targettype <> "TRASHBOX":
                        self.add_cardpocketmemory(header)
                    cw.cwpy.trade(targettype=targettype, header=header, from_event=True, party=backpack_party, sort=False)
                    n -= 1
            if targettype_original == "BACKPACK":
                cw.cwpy.ydata.party.sort_backpack()
            elif targettype_original == "STOREHOUSE":
                cw.cwpy.ydata.sort_storehouse()
            for header in self.cardpocket[cw.POCKET_SKILL]:
                header.get_uselimit(reset=True)
        elif 0 < uplevel and revert_cardpocket:
            # レベル調節で手放したカードを戻す
            self.revert_cardpocket(backpack_party)

    def add_cardpocketmemory(self, header):
        """レベル調節前に所持していたカードを記憶する。"""
        memories = self.data.find("./CardMemories")
        if memories is None:
            memories = cw.data.make_element("CardMemories")
            self.data.append(".", memories)
        e = cw.data.make_element("CardMemory")
        e.append(cw.data.make_element("Type", header.type))
        e.append(cw.data.make_element("Name", header.name))
        e.append(cw.data.make_element("Description", header.desc))
        e.append(cw.data.make_element("Scenario", header.scenario))
        e.append(cw.data.make_element("Author", header.author))
        if type <> "BeastCard":
            e.append(cw.data.make_element("Hold", str(header.hold)))
        if header.type <> "SkillCard":
            e.append(cw.data.make_element("UseLimit", str(header.uselimit)))
        memories.append(e)

    def revert_cardpocket(self, backpack_party=None):
        """記憶していたカードを検索し、
        見つかったら再び所持する。"""
        if not cw.cwpy.setting.revert_cardpocket:
            return

        if not backpack_party:
            backpack_party = cw.cwpy.ydata.party

        seq = []
        if backpack_party:
            seq.extend(backpack_party.backpack)
            if not backpack_party.is_adventuring():
                seq.extend(cw.cwpy.ydata.storehouse)
        else:
            seq.extend(cw.cwpy.ydata.storehouse)

        maxn = self.get_cardpocketspace()
        n = [
             len(self.get_pocketcards(cw.POCKET_SKILL)),
             len(self.get_pocketcards(cw.POCKET_ITEM)),
             len(self.get_pocketcards(cw.POCKET_BEAST)),
        ]
        for e in reversed(self.data.getfind("./CardMemories", False)[:]):
            cardtype = e.gettext("./Type")
            name = e.gettext("./Name", "")
            desc = e.gettext("./Description", "")
            scenario = e.gettext("./Scenario", "")
            author = e.gettext("./Author", "")
            if cardtype == "SkillCard":
                index = cw.POCKET_SKILL
                uselimit = -1
            elif cardtype == "ItemCard":
                index = cw.POCKET_ITEM
                uselimit = e.getint("./UseLimit", -1)
            elif cardtype == "BeastCard":
                index = cw.POCKET_BEAST
                uselimit = e.getint("./UseLimit", -1)

            if n[index] < maxn[index]:
                for header in seq:
                    if header.type == cardtype and\
                            header.name == name and\
                            header.desc == desc and\
                            header.scenario == scenario and\
                            header.author == author and\
                            (uselimit == -1 or uselimit == header.uselimit):
                        n[index] += 1
                        cw.cwpy.trade("PLAYERCARD", target=self, header=header, from_event=True, party=backpack_party)
                        seq.remove(header)
                        if cardtype <> "BeastCard":
                            hold = e.getbool("./Hold", False)
                            header.set_hold(hold)
                        break
                # 記憶に残すのは持ちきれなかった場合のみ
                # 持ちきれる場合はカードが見つからなくても
                # 記憶から除去する
                self.data.remove("./CardMemories", e)

    #---------------------------------------------------------------------------
    #　状態変更用
    #---------------------------------------------------------------------------

    def set_unconsciousstatus(self, clearbeast=True):
        """
        意識不明に伴う状態回復。
        強化値もすべて0、付帯召喚以外の召喚獣カードも消去。
        毒と麻痺は残る。
        """
        self.set_mentality("Normal", 0)
        self.set_bind(0)
        self.set_silence(0)
        self.set_faceup(0)
        self.set_antimagic(0)
        self.set_enhance_act(0, 0)
        self.set_enhance_avo(0, 0)
        self.set_enhance_res(0, 0)
        self.set_enhance_def(0, 0)
        if clearbeast:
            self.set_beast(vanish=True)

    def set_fullrecovery(self, decideaction=False):
        """
        完全回復処理。HP＆精神力＆状態異常回復。
        強化値もすべて0、付帯召喚以外の召喚獣カードも消去。
        """
        self.set_life(self.maxlife)
        self.set_paralyze(-40)
        self.set_poison(-40)
        self.set_mentality("Normal", 0)
        self.set_bind(0)
        self.set_silence(0)
        self.set_faceup(0)
        self.set_antimagic(0)
        self.set_enhance_act(0, 0)
        self.set_enhance_avo(0, 0)
        self.set_enhance_res(0, 0)
        self.set_enhance_def(0, 0)
        self.set_skillpower()
        self.set_beast(vanish=True)

        # 行動を再選択する
        if decideaction and cw.cwpy.is_battlestatus() and cw.cwpy.battle.is_ready() and self.is_active():
            self.deck.set(self)
            self.decide_action()

    def set_life(self, value):
        """
        現在ライフに引数nの値を足す(nが負だと引き算でダメージ)。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        oldlife = self.life
        self.life += value
        self.life = cw.util.numwrap(self.life, 0, self.maxlife)
        self.data.edit("Property/Life", str(int(self.life)))
        self.adjust_action()
        if self.is_unconscious():
            self.set_unconsciousstatus()
        return self.life - oldlife

    def set_paralyze(self, value):
        """
        麻痺値を操作する。
        麻痺値は0～40の範囲を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        old = self.paralyze
        self.paralyze += value
        self.paralyze = cw.util.numwrap(self.paralyze, 0, 40)
        if 0 < self.paralyze:
            self.set_mentality("Normal", 0)
        self.data.edit("Property/Status/Paralyze", str(self.paralyze))
        self.adjust_action()
        return self.paralyze - old

    def set_poison(self, value):
        """
        中毒値を操作する。
        中毒値は0～40の範囲を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        old = self.poison
        self.poison += value
        self.poison = cw.util.numwrap(self.poison, 0, 40)
        self.data.edit("Property/Status/Poison", str(self.poison))
        return self.poison - old

    def set_mentality(self, name, value, overwrite=True):
        """
        精神状態とその継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious() or self.is_paralyze():
            name = "Normal"
            value = 0
        value = cw.util.numwrap(value, 0, 999)
        if name == "Normal":
            value = 0
        elif value == 0:
            name = "Normal"

        if not overwrite and name == self.mentality and name <> "Normal":
            # 長い方の効果時間を優先
            self.mentality_dur = max(self.mentality_dur, value)
        else:
            self.mentality = name
            self.mentality_dur = value

        path = "Property/Status/Mentality"
        self.data.edit(path, self.mentality)
        self.data.edit(path, str(self.mentality_dur), "duration")
        self.adjust_action()

    def set_bind(self, value, overwrite=True):
        """
        束縛状態の継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
        if overwrite:
            self.bind = value
        else:
            self.bind = max(self.bind, value)
        self.bind = cw.util.numwrap(self.bind, 0, 999)
        self.data.edit("Property/Status/Bind", str(self.bind), "duration")
        self.adjust_action()

    def set_silence(self, value, overwrite=True):
        """
        沈黙状態の継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
        if overwrite:
            self.silence = value
        else:
            self.silence = max(self.silence, value)
        self.silence = cw.util.numwrap(self.silence, 0, 999)
        self.data.edit("Property/Status/Silence", str(self.silence), "duration")

    def set_faceup(self, value, overwrite=True):
        """
        暴露状態の継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
        if overwrite:
            self.faceup = value
        else:
            self.faceup = max(self.faceup, value)
        self.faceup = cw.util.numwrap(self.faceup, 0, 999)
        self.data.edit("Property/Status/FaceUp", str(self.faceup), "duration")

    def set_antimagic(self, value, overwrite=True):
        """
        魔法無効状態の継続ラウンド数を操作する。
        継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
        if overwrite:
            self.antimagic = value
        else:
            self.antimagic = max(self.antimagic, value)
        self.antimagic = cw.util.numwrap(self.antimagic, 0, 999)
        self.data.edit("Property/Status/AntiMagic", str(self.antimagic), "duration")

    def set_vanish(self, battlespeed=False):
        """
        対象消去を行う。
        """
        if isinstance(self, cw.character.Friend):
            # 1.50までは同行NPCに対象消去は効かない
            return
        if not self.is_vanished():
            if cw.cwpy.ydata:
                cw.cwpy.ydata.changed()
            self._vanished = True
            if isinstance(self, cw.character.Player):
                cw.animation.animate_sprite(self, "vanish", battlespeed=battlespeed)
                if cw.cwpy.sct.enable_vanishmembercancellation(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_SCENARIO)) or\
                   cw.cwpy.sct.enable_vanishmembercancellation(cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA)):
                    cw.cwpy.ydata.party.vanished_pcards.append(self)
                else:
                    self.commit_vanish()
            else:
                cw.animation.animate_sprite(self, "delete", battlespeed=battlespeed)
                self.commit_vanish()
            cw.cwpy.vanished_card(self)

    def cancel_vanish(self):
        """対象消去をキャンセルする。
        表示処理は行わないため、呼び出し後に行う必要がある。
        """
        if not self.is_vanished():
            return
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()

        assert not cw.cwpy.cardgrp.has(self)
        assert self.data in cw.cwpy.ydata.party.members

        self._vanished = False
        cw.cwpy.cardgrp.add(self, layer=self.layer)
        cw.cwpy.pcards.insert(cw.cwpy.ydata.party.members.index(self.data), self)

    def commit_vanish(self):
        if not self.is_vanished():
            return
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()

        if isinstance(self, cw.character.Player):
            # PCの場合、プレミアカードを荷物袋へ移動する
            for pocket in self.cardpocket:
                for card in pocket[:]:
                    if card.premium == "Premium":
                        cw.cwpy.trade("BACKPACK", header=card, from_event=True, sort=False)

            index = cw.cwpy.ydata.party.members.index(self.data)
            for i in xrange(index, len(cw.cwpy.ydata.party.members)):
                pi = i + 1
                cw.cwpy.file_updates.update(cw.cwpy.update_pcimage(pi, deal=False))

            for bgtype, d in cw.cwpy.background.bgs:
                if bgtype == cw.sprite.background.BG_PC:
                    pcnumber = d[0]
                    if index + 1 <= pcnumber:
                        cw.cwpy.file_updates_bg = True
                        break
                elif bgtype == cw.sprite.background.BG_TEXT:
                    namelist = d[1]
                    for item in namelist:
                        if item.data is self:
                            # テキストセルに表示中の名前
                            # 対象消去された場合は最後に表示された文字列に固定する
                            item.data = None

            cw.cwpy.ydata.party.remove(self)

        self.lost()

    def set_enhance_act(self, value, duration):
        """
        行動力強化値とその継続ラウンド数を操作する。
        強化値の範囲は-10～10、継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
            duration = 0
        if value == 0:
            duration = 0
        if duration <= 0:
            value = 0
        self.enhance_act = value
        self.enhance_act = cw.util.numwrap(self.enhance_act, -10, 10)
        self.enhance_act_dur = duration
        self.enhance_act_dur = cw.util.numwrap(self.enhance_act_dur, 0, 999)
        path = "Property/Enhance/Action"
        self.data.edit(path, str(self.enhance_act))
        self.data.edit(path, str(self.enhance_act_dur), "duration")

    def set_enhance_avo(self, value, duration):
        """
        回避力強化値とその継続ラウンド数を操作する。
        強化値の範囲は-10～10、継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
            duration = 0
        if value == 0:
            duration = 0
        if duration <= 0:
            value = 0
        self.enhance_avo = value
        self.enhance_avo = cw.util.numwrap(self.enhance_avo, -10, 10)
        self.enhance_avo_dur = duration
        self.enhance_avo_dur = cw.util.numwrap(self.enhance_avo_dur, 0, 999)
        path = "Property/Enhance/Avoid"
        self.data.edit(path, str(self.enhance_avo))
        self.data.edit(path, str(self.enhance_avo_dur), "duration")

    def set_enhance_res(self, value, duration):
        """
        抵抗力強化値とその継続ラウンド数を操作する。
        強化値の範囲は-10～10、継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
            duration = 0
        if value == 0:
            duration = 0
        if duration <= 0:
            value = 0
        self.enhance_res = value
        self.enhance_res = cw.util.numwrap(self.enhance_res, -10, 10)
        self.enhance_res_dur = duration
        self.enhance_res_dur = cw.util.numwrap(self.enhance_res_dur, 0, 999)
        path = "Property/Enhance/Resist"
        self.data.edit(path, str(self.enhance_res))
        self.data.edit(path, str(self.enhance_res_dur), "duration")

    def set_enhance_def(self, value, duration):
        """
        抵抗力強化値とその継続ラウンド数を操作する。
        強化値の範囲は-10～10、継続ラウンド数の範囲は0～999を越えない。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        if self.is_unconscious():
            value = 0
            duration = 0
        if value == 0:
            duration = 0
        if duration <= 0:
            value = 0
        self.enhance_def = value
        self.enhance_def = cw.util.numwrap(self.enhance_def, -10, 10)
        self.enhance_def_dur = duration
        self.enhance_def_dur = cw.util.numwrap(self.enhance_def_dur, 0, 999)
        path = "Property/Enhance/Defense"
        self.data.edit(path, str(self.enhance_def))
        self.data.edit(path, str(self.enhance_def_dur), "duration")

    def set_skillpower(self, value=999):
        """
        精神力(スキルの使用回数)を操作する。
        recoveryがTrueだったら、最大値まで回復。
        Falseだったら、0にする。
        """
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        for header in self.get_pocketcards(cw.POCKET_SKILL):
            header.set_uselimit(value)

        if 0 < value:
            if cw.cwpy.is_battlestatus():
                self.deck.get_skillpower(self)
        elif value < 0:
            if cw.cwpy.is_battlestatus():
                self.deck.lose_skillpower(self, -value)

    def set_beast(self, element=None, vanish=False, is_scenariocard=False):
        """召喚獣を召喚する。付帯召喚設定は強制的にクリアされる。
        vanish: 召喚獣を消去するかどうか。
        """
        idx = cw.POCKET_BEAST

        eff = False
        if vanish:
            for header in self.get_pocketcards(idx)[::-1]:
                if not header.attachment:
                    self.throwaway_card(header, update_image=False)
                    eff = True

        elif self.can_addbeast():
            if self.is_unconscious():
                return eff
            etree = cw.data.xml2etree(element=element, nocache=True)
            cw.content.get_card(etree, self, not is_scenariocard, update_image=False)
            eff = True
        return eff

    def can_addbeast(self):
        if self.is_unconscious():
            return False
        idx = cw.POCKET_BEAST
        return len(self.get_pocketcards(idx)) < self.get_cardpocketspace()[idx]

    def decrease_physical(self, stype, time):
        """中毒麻痺の時間経過による軽減。"""
        for _t in xrange(time):
            uvalue = cw.util.div_vocation(self.get_vocation_val(("vit", "aggressive"))) + self.level + cw.cwpy.dice.roll(2)
            tvalue = (self.poison if stype == "Poison" else self.paralyze) + cw.cwpy.dice.roll(2)

            flag = uvalue >= tvalue
            dice = cw.cwpy.dice.roll(2)
            if dice == 12:
                flag = True
            if dice == 2:
                flag = False

            if flag:
                if stype == "Poison":
                    self.set_poison(-1)
                else:
                    self.set_paralyze(-1)

    def set_timeelapse(self, time=1, fromevent=False):
        """時間経過。"""
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        # 時限クーポン処理
        self.count_timedcoupon()
        oldalive = self.is_alive()
        flag = False # 反転しながら画像を更新する場合はTrue
        updateimage = False # 反転せずに画像を更新する場合はTrue

        # 中毒
        if self.is_poison() and not self.is_unconscious():
            self.decrease_physical("Poison", time)

            if not self.is_poison():
                flag = True
                cw.cwpy.advlog.recover_poison(self)
            else:
                cw.cwpy.play_sound("dump")
                value = 1 * self.poison
                n = value / 5
                n2 = value % 5 * 2
                value = cw.cwpy.dice.roll(n, 10)

                if n2:
                    value += cw.cwpy.dice.roll(1, n2)

                oldlife = self.life
                value = self.set_life(-value)
                cw.cwpy.advlog.poison_damage(self, value, self.life, oldlife)

                if self.status <> "reversed" and self.status <> "hidden":
                    cw.animation.animate_sprite(self, "lateralvibe", battlespeed=cw.cwpy.is_battlestatus())
                self.update_image()
                cw.cwpy.draw(clip=self.rect)

        # 麻痺
        if self.is_paralyze() and not self.is_petrified() and not self.is_unconscious():
            self.decrease_physical("Paralyze", time)
            if not self.is_paralyze():
                cw.cwpy.advlog.recover_paralyze(self)
                flag = True
            if self.is_analyzable():
                updateimage = True

        # 束縛
        if self.is_bind():
            value = self.bind - time
            self.set_bind(value)
            if not self.is_bind():
                cw.cwpy.advlog.recover_bind(self)
                flag = True
            if self.is_analyzable():
                updateimage = True

        # 沈黙
        if self.is_silence():
            value = self.silence - time
            self.set_silence(value)
            if not self.is_silence():
                cw.cwpy.advlog.recover_silence(self)
                flag = True
            if self.is_analyzable():
                updateimage = True

        # 暴露
        if self.is_faceup():
            value = self.faceup - time
            self.set_faceup(value)
            if not self.is_faceup():
                cw.cwpy.advlog.recover_faceup(self)
                flag = True
            if self.is_analyzable():
                updateimage = True

        # 魔法無効化
        if self.is_antimagic():
            value = self.antimagic - time
            self.set_antimagic(value)
            if not self.is_antimagic():
                cw.cwpy.advlog.recover_antimagic(self)
                flag = True
            if self.is_analyzable():
                updateimage = True

        # 精神状態
        if self.mentality_dur > 0:
            value = self.mentality_dur - time

            if value > 0:
                self.set_mentality(self.mentality, value)
            else:
                cw.cwpy.advlog.recover_mentality(self, self.mentality)
                self.set_mentality("Normal", 0)
                flag = True

            if self.is_analyzable():
                updateimage = True

        # 行動力
        if self.enhance_act_dur > 0:
            value = self.enhance_act_dur - time

            if value > 0:
                self.set_enhance_act(self.enhance_act, value)
            else:
                cw.cwpy.advlog.recover_enhance_act(self)
                self.set_enhance_act(0, 0)
                flag = True

            if self.is_analyzable():
                updateimage = True

        # 回避力
        if self.enhance_avo_dur > 0:
            value = self.enhance_avo_dur - time

            if value > 0:
                self.set_enhance_avo(self.enhance_avo, value)
            else:
                cw.cwpy.advlog.recover_enhance_avo(self)
                self.set_enhance_avo(0, 0)
                flag = True

            if self.is_analyzable():
                updateimage = True

        # 抵抗力
        if self.enhance_res_dur > 0:
            value = self.enhance_res_dur - time

            if value > 0:
                self.set_enhance_res(self.enhance_res, value)
            else:
                cw.cwpy.advlog.recover_enhance_res(self)
                self.set_enhance_res(0, 0)
                flag = True

            if self.is_analyzable():
                updateimage = True

        # 防御力
        if self.enhance_def_dur > 0:
            value = self.enhance_def_dur - time

            if value > 0:
                self.set_enhance_def(self.enhance_def, value)
            else:
                cw.cwpy.advlog.recover_enhance_def(self)
                self.set_enhance_def(0, 0)
                flag = True

            if self.is_analyzable():
                updateimage = True

        # 中毒効果で死亡していたら、ステータスを元に戻す
        if self.is_unconscious():
            self.set_unconsciousstatus()

        # 画像更新
        if flag or updateimage:
            if self.status <> "reversed" and self.status <> "hidden":
                if flag:
                    battlespeed = cw.cwpy.is_battlestatus()
                    cw.animation.animate_sprite(self, "hide", battlespeed=battlespeed)
                    self.update_image()
                    cw.animation.animate_sprite(self, "deal", battlespeed=battlespeed)
                else:
                    self.update_image()
            else:
                self.update_image()
            cw.cwpy.draw(clip=self.rect)

        # エネミーまたはプレイヤー(Wsn.2)が中毒効果で死亡していたら、死亡イベント開始
        if isinstance(self, (Player, Enemy)) and self.is_dead() and oldalive:
            if isinstance(self, Player):
                # プレイヤーカードのキーコード・死亡時イベント(Wsn.2)
                events = cw.cwpy.sdata.playerevents
            else:
                events = self.events

            if events:
                e_eventtarget = None
                if fromevent:
                    for t in itertools.chain(cw.cwpy.get_pcards(), cw.cwpy.get_ecards(), cw.cwpy.get_fcards()):
                        if isinstance(t, cw.character.Character):
                            if t.has_coupon(u"＠イベント対象"):
                                e_eventtarget = t
                                t.remove_coupon(u"＠イベント対象")
                                break

                try:
                    if cw.cwpy.sdata.is_wsnversion('2'):
                        # イベント所持者を示すシステムクーポン(Wsn.2)
                        self.set_coupon(u"＠イベント対象", 0)
                    if fromevent:
                        event = events.check_keynum(1)
                        if event:
                            event.run_scenarioevent()
                    else:
                        events.start(1, isinsideevent=False)
                finally:
                    self.remove_coupon(u"＠イベント対象")

                    if e_eventtarget:
                        e_eventtarget.set_coupon(u"＠イベント対象", 0)

    def set_hold_all(self, pocket, value):
        self.hold_all[pocket] = value
        if pocket == cw.POCKET_SKILL:
            type = "SkillCards"
        elif pocket == cw.POCKET_ITEM:
            type = "ItemCards"
        elif pocket == cw.POCKET_BEAST:
            type = "BeastCards"
        else:
            assert False
        self.data.edit(type, str(value), "hold_all")

class Player(Character):
    def lost(self):
        if cw.cwpy.ydata:
            cw.cwpy.ydata.changed()
        self.remove_numbercoupon()
        self.remove_timedcoupons()
        self.data.edit("Property", "True", "lost")
        self.data.write_xml()
        if cw.cwpy.is_playingscenario():
            if self.data.fpath.lower().startswith("yado"):
                fpath = cw.util.relpath(self.data.fpath, cw.cwpy.ydata.yadodir)
            else:
                fpath = cw.util.relpath(self.data.fpath, cw.cwpy.ydata.tempdir)
            fpath = cw.util.join_paths(fpath)
            cw.cwpy.sdata.lostadventurers.add(fpath)
        if cw.cwpy.cardgrp.has(self):
            cw.cwpy.cardgrp.remove(self)
            cw.cwpy.pcards.remove(self)

    def set_name(self, name):
        Character.set_name(self, name)
        if cw.cwpy.ydata:
            for header in cw.cwpy.ydata.partyrecord:
                header.rename_member(self.data.fpath, name)
        cw.cwpy.background.reload(False, nocheckvisible=True)

def calc_maxlife(vit, minval, level):
    """能力値から体力の最大値を計算する。"""
    vit = max(1, vit)
    minval = max(1, minval)
    level = max(1, level)
    return int((float(vit) / 2.0 + 4) * (level + 1) + float(minval) / 2.0)
assert calc_maxlife(8, 5, 10) == 90
assert calc_maxlife(9, 5, 10) == 96

class Enemy(Character):
    def is_dead(self):
        """
        敵は隠蔽状態であれば死亡と見做す。
        """
        b = Character.is_dead(self)
        b |= self.status == "hidden"
        return b

    def is_inactive(self, check_reversed=True):
        """
        敵は隠蔽状態であれば行動不能と見做す。
        """
        b = Character.is_inactive(self, check_reversed=check_reversed)
        b |= self.status == "hidden"
        return b

class Friend(Character):
    pass

class AlbumPage(object):
    def __init__(self, data):
        self.data = data
        self.name = self.data.gettext("Property/Name", "")
        self.level = cw.util.numwrap(self.data.getint("Property/Level"), 1, 65536)

    def get_specialcoupons(self):
        """
        "＠"で始まる特殊クーポンの
        辞書(key=クーポン名, value=クーポン得点)を返す。
        """
        d = {}

        for e in self.data.getfind("Property/Coupons"):
            coupon = e.text
            if coupon and coupon.startswith(u"＠"):
                d[coupon] = int(e.get("value", "0"))

        return d

def main():
    pass

if __name__ == "__main__":
    main()

