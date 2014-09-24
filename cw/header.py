#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import re
import copy
import weakref
import StringIO
import wx
import pygame
import xml.parsers.expat
import shutil

import cw


class CardHeader(object):
    def __init__(self, data=None, owner=None, carddata=None, from_scenario=False, scedir="", put_db=False, dbrec=None, dbowner="STOREHOUSE", bgtype=""):
        self.ref_original = weakref.ref(self)
        self.order = -1
        if dbrec:
            self.set_owner(dbowner)
            self.carddata = None
            self.fpath = dbrec["fpath"]
            self.type = dbrec["type"]
            self.id = dbrec["id"]
            self.name = dbrec["name"]
            self.imgpath = dbrec["imgpath"]
            self.desc = dbrec["desc"]
            self.scenario = dbrec["scenario"]
            self.author = dbrec["author"]
            self.keycodes = dbrec["keycodes"].split("\n")
            self.uselimit = dbrec["uselimit"]
            self.target = dbrec["target"]
            self.allrange = bool(dbrec["allrange"])
            self.premium = dbrec["premium"]
            self.physical = dbrec["physical"]
            self.mental = dbrec["mental"]
            self.level = dbrec["level"]
            self.maxuselimit = dbrec["maxuselimit"]
            self.price = dbrec["price"]
            self.hold = bool(dbrec["hold"])
            self.enhance_avo = dbrec["enhance_avo"]
            self.enhance_res = dbrec["enhance_res"]
            self.enhance_def = dbrec["enhance_def"]
            self.enhance_avo_used = dbrec["enhance_avo_used"]
            self.enhance_res_used = dbrec["enhance_res_used"]
            self.enhance_def_used = dbrec["enhance_def_used"]
            self.attachment = bool(dbrec["attachment"])
            if dbowner == "BACKPACK":
                from_scenario = bool(dbrec["scenariocard"])
            self.versionhint = cw.cwpy.sct.from_basehint(dbrec["versionhint"])
            self.moved = dbrec["moved"]
            self.star = dbrec["star"]
        else:
            self.set_owner(owner)
            self.carddata = carddata

            if data is not None:
                self.fpath = data.fpath
                self.type = os.path.basename(os.path.dirname(self.fpath))
            elif carddata is not None:
                self.fpath = ""
                self.type = carddata.tag
                data = carddata.getfind("Property")

            self.id = data.getint("Id", 0)
            self.name = data.gettext("Name", "")
            self.desc = data.gettext("Description", "")
            self.scenario = data.gettext("Scenario", "")
            self.author = data.gettext("Author", "")
            self.keycodes = data.gettext("KeyCodes", "")
            self.keycodes = cw.util.decodetextlist(self.keycodes) if self.keycodes else []
            self.uselimit = data.getint("UseLimit", 0)
            self.target = data.gettext("Target", "None")
            self.allrange = data.getbool("Target", "allrange", False)
            self.premium = data.gettext("Premium", "Normal")
            self.physical = data.getattr("Ability", "physical", "None").lower()
            self.mental = data.getattr("Ability", "mental", "None").lower()
            # カードの種類ごとに違う処理
            self.level = 9999
            self.maxuselimit = 0
            self.price = 0
            self.hold = False
            self.enhance_avo = 0
            self.enhance_res = 0
            self.enhance_def = 0
            self.enhance_avo_used = 0
            self.enhance_res_used = 0
            self.enhance_def_used = 0
            self.attachment = False
            self.moved = data.getint(".", "moved", 0)
            self.star = data.getint("Star", 0)

            if self.type == "ActionCard":
                self.enhance_avo_used = data.getint("Enhance", "avoid")
                self.enhance_res_used = data.getint("Enhance", "resist")
                self.enhance_def_used = data.getint("Enhance", "defense")
            elif self.type == "SkillCard":
                self.level = data.getint("Level")
                self.hold = data.getbool("Hold")
                self.enhance_avo_used = data.getint("Enhance", "avoid")
                self.enhance_res_used = data.getint("Enhance", "resist")
                self.enhance_def_used = data.getint("Enhance", "defense")
                self.price = 200 + self.level * 100
            elif self.type == "ItemCard":
                self.maxuselimit = data.getint("UseLimit", "max")
                self.enhance_avo = data.getint("EnhanceOwner", "avoid")
                self.enhance_res = data.getint("EnhanceOwner", "resist")
                self.enhance_def = data.getint("EnhanceOwner", "defense")
                self.enhance_avo_used = data.getint("Enhance", "avoid")
                self.enhance_res_used = data.getint("Enhance", "resist")
                self.enhance_def_used = data.getint("Enhance", "defense")
                self.hold = data.getbool("Hold")
                self.price = data.getint("Price")
            elif self.type == "BeastCard":
                self.maxuselimit = data.getint("UseLimit")
                self.enhance_avo = data.getint("Enhance", "avoid")
                self.enhance_res = data.getint("Enhance", "resist")
                self.enhance_def = data.getint("Enhance", "defense")
                if data.hasfind("Attachment"):
                    self.attachment = data.getbool("Attachment")
                elif self.is_ccardheader():
                    self.attachment = True if self.uselimit == 0 else False
                    e = cw.data.make_element("Attachment", str(self.attachment))
                    data.append(e)
                self.price = 1000

            # Image
            self.imgpath = data.gettext("ImagePath", "")
            # 互換性マーク
            self.versionhint = cw.cwpy.sct.from_basehint(data.getattr(".", "versionHint", ""))

        self.bgtype = bgtype

        self.vocation = (self.physical, self.mental)

        self._cardscale = cw.UP_SCR
        self._wxcardscale = cw.UP_WIN
        self._skindirname = cw.cwpy.setting.skindirname

        # スキルカードと召喚獣カードは価格固定
        if self.type == "SkillCard":
            self.price = 400 + self.level * 200
        elif self.type == "BeastCard":
            self.price = 1000

        # シナリオ取得フラグ
        if from_scenario or (self.carddata is not None and self.carddata.get("scenariocard")):
            self.scenariocard = True
            if scedir:
                self.scedir = scedir
            else:
                self.scedir = cw.cwpy.sdata.scedir
        else:
            self.scenariocard = False
            self.scedir = ""
        # 画像設定
        self._cardimg = None
        self.rect = cw.s(pygame.Rect(0, 0, 80, 110))
        self.wxrect = cw.wins(pygame.Rect(0, 0, 80, 110))
        # cardcontrolダイアログで使うフラグ
        self.negaflag = False
        self.clickedflag = False

        # 特殊なキーコード
        self.keycodes.append(self.name)
        self.penalty = bool(u"ペナルティ" in self.keycodes)
        self.recycle = bool(u"リサイクル" in self.keycodes)

        # 所持スキルカードだった場合は使用回数を設定
        if self.is_ccardheader() and self.type == "SkillCard":
            self.get_uselimit()

        # ソート用の型ID
        if self.type == "SkillCard":
            self.type_id = 0
        elif self.type == "ItemCard":
            self.type_id = 1
        else:
            self.type_id = 2

    @property
    def negastar(self):
        return -self.star

    def set_cardimg(self, path):
        if not cw.binary.image.path_is_code(path):
            if self.type in ("ActionCard", "UseCardInBackpack"):
                path = cw.util.join_paths(cw.cwpy.skindir, path)
            elif self.scenariocard:
                path = cw.util.get_materialpath(path, cw.M_IMG, scedir=self.scedir)
            else:
                path = cw.util.join_yadodir(path)

        imgpath = path
        # TODO scaleinfo
        self._cardimg = cw.image.CardImage(imgpath, self.get_bgtype(),
                                                    self.name, self.premium)
        self.rect = pygame.Rect(self.rect)
        self.rect.size = self._cardimg.rect.size
        self.wxrect = pygame.Rect(self._cardimg.wxrect)
        self._cardscale = cw.UP_SCR
        self._wxcardscale = cw.UP_WIN
        self._skindirname = cw.cwpy.setting.skindirname

    def get_owner(self):
        if self._owner == "BACKPACK":
            return cw.cwpy.ydata.party.backpack
        elif self._owner == "STOREHOUSE":
            return cw.cwpy.ydata.storehouse
        elif self._owner:
            return self._owner()
        else:
            return None

    def set_owner(self, owner):
        if isinstance(owner, cw.character.Character):
            self._owner = weakref.ref(owner)
        else:
            self._owner = owner

    def get_bgtype(self):
        if self.bgtype:
            return self.bgtype
        if self.type == "BeastCard" and self.attachment:
            return "OPTION"
        return self.type.upper().replace("CARD", "")

    @property
    def cardimg(self):
        if not self._cardimg or self._cardscale <> cw.UP_SCR or\
                self._wxcardscale <> cw.UP_WIN or\
                self._skindirname <> cw.cwpy.setting.skindirname:
            self.set_cardimg(self.imgpath)
        return self._cardimg

    def get_cardwxbmp(self):
        return self.cardimg.get_cardwxbmp(self)

    def get_cardimg(self):
        return self.cardimg.get_cardimg(self)

    def get_vocation_level(self, owner, enhance_act=False):
        """
        適性値の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
        enhance_act : 行動力を加味する場合、True
        """
        value = self.get_vocation_val(owner, enhance_act)

        if value < 3:
            value = 0
        elif value < 9:
            value = 1
        elif value < 15:
            value = 2
        elif value < 20:
            value = 3
        else:
            value = 4

        return value

    def get_vocation_val(self, owner, enhance_act=False):
        """
        適性値(身体特性+精神特性の合計値)を返す。
        enhance_act : 行動力を加味する場合、True
        """
        if not owner:
            owner = self.get_owner()
        physical = self.vocation[0]
        mental = self.vocation[1].replace("un", "", 1)
        physical = owner.data.getint("Property/Ability/Physical", physical, 0)
        mental = owner.data.getint("Property/Ability/Mental", mental, 0)

        if self.vocation[1].startswith("un"):
            mental = -mental

        if enhance_act:
            return physical + mental + owner.data.getint("Property/Enhance/Action")
        else:
            return physical + mental

    def get_uselimit_level(self):
        """
        使用回数の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
        """
        limit, maxlimit = self.get_uselimit()
        limitper = 100 * limit / maxlimit

        if limitper == 100:
            value = 4
        elif limit == 1: # MAX状態以外で残り1回なら
            value = 1
        elif limitper > 50:
            value = 3
        elif 50 >= limitper > 0:
            value = 2
        elif limitper ==   0:
            value = 0

        return value

    def get_uselimit(self, reset=False):
        """
        (使用回数, 最大使用回数)を返す。
        """
        if self.is_ccardheader() and self.type == "SkillCard"\
                    and (not self.maxuselimit or reset==True):
            owner = self.get_owner()
            level = owner.data.getint("Property/Level")
            value = level - self.level

            if value <= -3:
                self.maxuselimit = 1
            elif value == -2:
                self.maxuselimit = 2
            elif value == -1:
                self.maxuselimit = 3
            elif value == 0:
                self.maxuselimit = 5
            elif value == 1:
                self.maxuselimit = 7
            elif value == 2:
                self.maxuselimit = 8
            elif value >= 3:
                self.maxuselimit = 9

            if cw.cwpy.status == "Yado" or\
                    not isinstance(self.get_owner(), cw.character.Player)or\
                    self.uselimit > self.maxuselimit:
                self.uselimit = self.maxuselimit

        return self.uselimit, self.maxuselimit

    def get_enhance_val_used(self):
        """
        カード使用時に設定されている強化値を、
        (回避値, 抵抗値, 防御値)の順のタプルで返す。
        """
        if self.type in ("ActionCard", "SkillCard", "ItemCard"):
            return self.enhance_avo_used, self.enhance_res_used, self.enhance_def_used
        else:
            return 0, 0, 0

    def get_enhance_val(self):
        """
        カード所持時に設定されている強化値を、
        (回避値, 抵抗値, 防御値)の順のタプルで返す。
        """
        if self.type in ("ItemCard", "BeastCard"):
            return self.enhance_avo, self.enhance_res, self.enhance_def
        else:
            return 0, 0, 0

    def set_uselimit(self, value):
        """
        カードの使用回数を操作する。
        value: 増減値。
        """
        # アクションカード・未所持カードの場合は処理中止
        if self.type == "ActionCard" or not self.is_ccardheader():
            return

        # 戦闘時はCardHeaderインスタンスのコピーを使用するため、
        # 誤ったインスタンスを操作しないよう元のインスタンスを参照
        header = self.ref_original()
        if not header:
            # 使用時イベントで消滅した場合はここへ来る
            return

        owner = header.get_owner()

        # スキルカード。
        if header.type == "SkillCard":
            header.uselimit += value
            header.uselimit = cw.util.numwrap(header.uselimit, 0,
                                                            header.maxuselimit)
            e = header.carddata.getfind("Property/UseLimit")
            e.text = str(header.uselimit)
            owner.data.is_edited = True
        # アイテムカード。
        elif header.type == "ItemCard" and not header.maxuselimit == 0:
            header.uselimit += value
            header.uselimit = cw.util.numwrap(header.uselimit, 0, 999)
            e = header.carddata.getfind("Property/UseLimit")
            e.text = str(header.uselimit)
            owner.data.is_edited = True

            # カード消滅処理。リサイクルカードの場合は消滅させない
            if header.uselimit <= 0 and not header.recycle and header.get_owner() == owner:
                if cw.cwpy.battle and header in owner.deck.hand:
                    owner.deck.hand.remove(header)

                cw.cwpy.trade("TRASHBOX", header=header, from_event=True, clearinusecard=False)

        # 召喚獣カード。
        elif header.type == "BeastCard" and not header.maxuselimit == 0:
            header.uselimit += value
            header.uselimit = cw.util.numwrap(header.uselimit, 0, 999)
            e = header.carddata.getfind("Property/UseLimit")
            e.text = str(header.uselimit)
            owner.data.is_edited = True

            # カード消滅処理
            if header.uselimit <= 0:
                # 召喚獣消去効果で消えてる場合もあるのでチェック
                if header in owner.cardpocket[cw.POCKET_BEAST] and header.get_owner() == owner:
                    cw.cwpy.trade("TRASHBOX", header=header, from_event=True, clearinusecard=False)

    def write(self, party=None, move=False):
        def create_newpath(party):
            fname = cw.util.repl_dischar(self.name) + ".xml"
            if self._owner == "BACKPACK":
                if not party:
                    party = cw.cwpy.ydata.party
                dpath = os.path.dirname(party.path)
            else:
                dpath = cw.cwpy.yadodir
            path = cw.util.join_paths(dpath, self.type, fname)
            return cw.util.dupcheck_plus(path)

        if move:
            assert self.fpath
            topath = create_newpath(party)

            if topath.startswith(cw.cwpy.yadodir):
                topath = topath.replace(cw.cwpy.yadodir, cw.cwpy.tempdir, 1)

            dpath = os.path.dirname(topath)
            if not os.path.isdir(dpath):
                os.makedirs(dpath)

            if self.fpath.startswith(cw.cwpy.tempdir):
                # すでにtempdirにあるファイルならそのまま移動
                cw.cwpy.ydata.deletedpaths.discard(self.fpath)
                shutil.move(self.fpath, topath)
            else:
                # yadodirにあるファイルはコピーする必要がある
                shutil.copy(self.fpath, topath)

            cw.cwpy.ydata.deletedpaths.add(self.fpath)
            self.fpath = topath
            if self.fpath in cw.cwpy.ydata.deletedpaths:
                cw.cwpy.ydata.deletedpaths.remove(self.fpath)
        else:
            if self.carddata is None:
                return

            if self.fpath:
                path = self.fpath
            else:
                path = create_newpath(party)
                self.fpath = path

            etree = cw.data.xml2etree(element=self.carddata)
            etree.fpath = self.fpath

            if not self.type == "BeastCard":
                etree.edit("Property/Hold", "False")

            etree.write_xml(True)
            self.fpath = etree.fpath
        # self.fpathを削除予定のfpathリストから削除
        cw.cwpy.ydata.deletedpaths.discard(self.fpath)

    def contain_xml(self):
        if self.carddata is None:
            e = cw.data.yadoxml2etree(self.fpath)
            self.carddata = e.getroot()
            # self.fpathを削除予定のfpathリストに追加
            cw.cwpy.ydata.deletedpaths.add(self.fpath, self.scenariocard)

    def set_scenariostart(self):
        """
        シナリオ開始時に呼ばれる。
        """
        if self.is_ccardheader() and self.type == "SkillCard":
            e = self.carddata.getfind("Property/UseLimit")
            e.text = str(self.uselimit)
            owner = self.get_owner()
            owner.data.is_edited = True
        elif self.is_backpackheader() and self.scenariocard and self.carddata:
            path = self.carddata.gettext("Property/ImagePath", "")
            self.set_cardimg(path)

    def set_scenarioend(self):
        """
        シナリオ終了時に呼ばれる。
        非付帯召喚カードを削除したり、
        シナリオで取得したカードの素材ファイルを宿にコピーしたりする。
        """
        if self.scenariocard:
            if self.carddata is None:
                assert self.fpath, self.name
                assert os.path.isfile(self.fpath), self.fpath
                self.carddata = cw.data.xml2element(self.fpath)

            # シナリオ取得フラグクリア
            self.scenariocard = False
            self.carddata.attrib.pop("scenariocard")
            # 画像コピー
            dstdir = cw.util.join_paths(cw.cwpy.yadodir,
                                            "Material", self.type, self.name)
            dstdir = cw.util.dupcheck_plus(dstdir)
            cw.cwpy.copy_materials(self.carddata, dstdir)
            # 画像更新
            path = self.carddata.gettext("Property/ImagePath", "")
            self.imgpath = path
            self.set_cardimg(path)
            if self.is_backpackheader():
                self.write()
                self.carddata = None

        elif self.type == "BeastCard" and not self.attachment:
            cw.cwpy.trade("TRASHBOX", header=self, from_event=True)

        if self.is_ccardheader() and self.type == "SkillCard" and not self.carddata is None:
            self.carddata.getfind("Property/UseLimit").text = "0"

        if self.is_ccardheader():
            owner = self.get_owner()
            owner.data.is_edited = True
        elif self.is_backpackheader():
            cw.cwpy.ydata.party.data.is_edited = True

    def copy(self):
        """
        Deckクラスで呼ばれる用。
        CardImageインスタンスを新しく生成して返す。
        """
        header = copy.copy(self)
        header.set_cardimg(self.imgpath)
        return header

    def is_ccardheader(self):
        return bool(isinstance(self._owner, weakref.ref))

    def is_backpackheader(self):
        return bool(self._owner == "BACKPACK")

    def is_storehouseheader(self):
        return bool(self._owner == "STOREHOUSE")

    def is_autoselectable(self):
        # 対象無し
        card = self.ref_original()
        flag = not bool(card.target == "None")

        # 使用時ボーナス・ペナルティがあるカードは無条件に選択可能
        if not card.hold:
            if card.enhance_avo_used <> 0 or\
               card.enhance_res_used <> 0 or\
               card.enhance_def_used <> 0:
                return True

        # ペナルティカードは無条件に選択可能(ホールドも不可)
        if card.type <> "BeastCard" and card.penalty:
            return True

        if not card.carddata is None:
            # 効果無し
            flag &= not card.carddata.find("Motions/Motion") is None

        if card.type <> "BeastCard":
            # ホールド
            flag &= not card.hold

            if card.type == "ItemCard":
                # 使用回数0(リサイクルカードのみ)
                flag &= not bool(card.recycle and card.uselimit <= 0)

            owner = card.get_owner()
            if not card.carddata is None and owner:
                # 沈黙
                spell = card.carddata.getbool("Property/EffectType", "spell", False)
                flag &= not (owner.is_silence() and spell)

                # 魔法無効状態
                effecttype = card.carddata.gettext("Property/EffectType", "")
                magic = effecttype in ("Magic", "PhysicalMagic")
                flag &= not (owner.is_antimagic() and magic)

        return flag

    def get_targets(self):
        """
        (ターゲットのリスト,
         効果のあるターゲットのリスト,
         優先すべきターゲットのリスト)
        を返す。
        """
        owner = self.get_owner()

        if self.target == "Both":
            targets = cw.cwpy.get_pcards("unreversed")[:]
            targets.extend(cw.cwpy.get_ecards("unreversed"))
        elif self.target == "Party":
            if isinstance(owner, cw.character.Enemy):
                targets = cw.cwpy.get_ecards("unreversed")[:]
            else:
                targets = cw.cwpy.get_pcards("unreversed")[:]

        elif self.target == "Enemy":
            if isinstance(owner, cw.character.Enemy):
                targets = cw.cwpy.get_pcards("unreversed")[:]
            else:
                targets = cw.cwpy.get_ecards("unreversed")[:]

        elif self.target == "User":
            targets = [owner]
        elif self.target == "None":
            targets = []

        effective, highpriority = cw.effectmotion.get_effectivetargets(self, targets)
        return targets, effective, highpriority

    def is_noeffect(self, target):
        effecttype = self.carddata.gettext("Property/EffectType", "")
        if cw.effectmotion.check_noeffect(effecttype, target):
            return True
        for e in self.carddata.getfind("Motions"):
            element = e.getattr(".", "element", "")
            if not cw.effectmotion.is_noeffect(element, target):
                return False
        return True

    def get_keycodes(self):
        # 互換動作: 1.20以前にカード名キーコードは存在しない
        if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA)):
            return self.keycodes[:-1]
        else:
            return self.keycodes

    def set_hold(self, hold):
        if self.type == "BeastCard":
            return

        cw.cwpy.ydata.changed()
        self.hold = hold
        owner = self.get_owner()
        if isinstance(owner, cw.character.Player):
            etree = cw.data.CWPyElementTree(element=self.carddata)
            etree.edit("Property/Hold", str(self.hold))
            owner.data.is_edited = True

    def set_star(self, star):
        if self.star == star:
            return

        cw.cwpy.ydata.changed()
        self.star = star
        owner = self.get_owner()
        if isinstance(owner, cw.character.Player):
            data = cw.data.CWPyElementTree(element=self.carddata)
            e = data.find("Property/Star")
            if e is None:
                e = data.find("Property")
                e.append(cw.data.make_element("Star", str(self.star)))
                data.is_edited = True
            else:
                data.edit("Property/Star", str(self.star))
            owner.data.is_edited = True
        else:
            data = cw.data.CWPyElementTree(self.fpath)
            e = data.find("Property/Star")
            if e is None:
                e = data.find("Property")
                e.append(cw.data.make_element("Star", str(self.star)))
                data.is_edited = True
            else:
                data.edit("Property/Star", str(self.star))
            data.write_xml()
            self.fpath = data.fpath

class InfoCardHeader(object):
    def __init__(self, data):
        """
        情報カードのヘッダ。引数のdataはPropertyElement。
        """
        # 各種データ
        self.id = data.getint("Id", 0)
        self.name = data.gettext("Name", "")
        self.desc = data.gettext("Description", "")
        self.scenario = cw.cwpy.sdata.name
        self.author = cw.cwpy.sdata.author
        # 画像
        path = data.gettext("ImagePath", "")
        path = cw.util.get_materialpath(path, cw.M_IMG)
        self.imgpath = path
        self.set_cardimg()
        # cardcontrolダイアログで使うフラグ
        self.negaflag = False
        self.clickedflag = False

    def set_cardimg(self):
        # TODO scaleinfo
        self._cardimg = cw.image.CardImage(self.imgpath, "INFO", self.name)
        self.rect = self._cardimg.rect
        self.wxrect = self._cardimg.wxrect
        self._cardscale = cw.UP_SCR
        self._wxcardscale = cw.UP_WIN
        self._skindirname = cw.cwpy.setting.skindirname

    @property
    def cardimg(self):
        if self._cardscale <> cw.UP_SCR or\
                self._wxcardscale <> cw.UP_WIN or\
                self._skindirname <> cw.cwpy.setting.skindirname:
            self.set_cardimg()
        return self._cardimg

    def get_cardwxbmp(self):
        if self.negaflag:
            return self.cardimg.get_wxnegabmp()
        else:
            return self.cardimg.get_wxbmp()

    def get_cardimg(self):
        if self.negaflag:
            return self.cardimg.get_negaimg()
        else:
            return self.cardimg.get_image()

class AdventurerHeader(object):
    def __init__(self, data=None, album=False, dbrec=None):
        """
        album: アルバム用の場合はTrueにする。
        dbrec: データベースから生成する場合は対象レコード。
        冒険者のヘッダ。引数のdataはPropertyElement。
        """
        self.order = -1
        if dbrec:
            self.fpath = dbrec["fpath"]
            self.level = dbrec["level"]
            self.name = dbrec["name"]
            self.imgpath = dbrec["imgpath"]
            self.album = bool(dbrec["album"])
            self.lost = bool(dbrec["lost"])
            self.sex = dbrec["sex"]
            self.age = dbrec["age"]
            self.ep = dbrec["ep"]
            self.leavenoalbum = bool(dbrec["leavenoalbum"])
            self.gene = Gene()
            self.gene.set_str(dbrec["gene"])
            self.history = dbrec["history"].split("\n")
            self.race = dbrec["race"]
            self.versionhint = cw.cwpy.sct.from_basehint(dbrec["versionhint"])
        else:
            self.fpath = data.fpath
            self.level = data.getint("Level", 0)
            self.name = data.gettext("Name", "")
            self.imgpath = data.gettext("ImagePath", "")
            self.album = album

            # シナリオプレイ中にロストしたかどうかのフラグ
            if data.hasfind(".", "lost"):
                self.lost = True
            else:
                self.lost = False

            # クーポンにある各種変数取得
            ages = set(cw.cwpy.setting.periodcoupons)
            sexs = set(cw.cwpy.setting.sexcoupons)
            hiddens = set([u"＿", u"＠"])
            r_gene = re.compile(u"＠Ｇ\d{10}$")
            self.sex = cw.cwpy.setting.sexcoupons[0]
            self.age = cw.cwpy.setting.periodcoupons[0]
            self.ep = 0
            self.leavenoalbum = False
            self.gene = Gene()
            self.gene.set_randombit()
            self.history = []
            self.race = ""
            # 互換性マーク
            self.versionhint = cw.cwpy.sct.from_basehint(data.getattr(".", "versionHint", ""))

            for e in reversed(data.getfind("Coupons").getchildren()):
                if not e.text:
                    continue
                elif e.text in ages:
                    self.age = e.text
                elif e.text in sexs:
                    self.sex = e.text
                elif e.text == u"＠ＥＰ":
                    self.ep = int(e.get("value", 0))
                elif e.text == u"＿消滅予約":
                    self.leavenoalbum = True
                elif r_gene.match(e.text):
                    self.gene.set_str(e.text[2:], int(e.get("value", 0)))
                elif e.text.startswith(u"＠Ｒ"):
                    self.race = e.text[2:]
                elif len(self.history) < 7 and not e.text[0] in hiddens:
                    self.history.append(e.text)

                    if len(self.history) == 6:
                        self.history.append(u"etc...")

    def made_baby(self):
        """
        EP減少と子作り回数加算を行ったXMLファイルを書き出す。
        """
        if self.album:
            n = 10
        else:
            n = 0
            for period in cw.cwpy.setting.periods:
                if self.age == u"＿" + period.name:
                    n = period.spendep
                    break
            if n == 0:
                return

        self.ep -= n
        data = cw.data.yadoxml2etree(self.fpath)
        r_gene = re.compile(u"＠Ｇ\d{10}$")

        for e in data.getfind("Property/Coupons"):
            if not e.text:
                continue

            # EP減少
            if e.text == u"＠ＥＰ":
                e.attrib["value"] = str(e.getint(".", "value") - n)
            # 子作り回数加算
            elif r_gene.match(e.text):
                e.attrib["value"] = str(e.getint(".", "value") + 1)
                self.gene.count += 1

        data.write_xml(True)

    def grow(self):
        """
        年代変更後のXMLを書き出す。
        このメソッドでは永眠処理は行わない。
        """
        if self.album:
            return

        index = cw.cwpy.setting.periodcoupons.index(self.age)
        if index < 0:
            return

        if index == len(cw.cwpy.setting.periodcoupons) - 1:
            return

        nextage= cw.cwpy.setting.periodcoupons[index + 1]
        data = cw.data.yadoxml2etree(self.fpath)

        # 能力値を再調整
        p = data.find("Property/Ability/Physical")
        m = data.find("Property/Ability/Mental")
        data.dex = p.getint(".", "dex", 0)
        data.agl = p.getint(".", "agl", 0)
        data.int = p.getint(".", "int", 0)
        data.str = p.getint(".", "str", 0)
        data.vit = p.getint(".", "vit", 0)
        data.min = p.getint(".", "min", 0)
        data.aggressive = m.getfloat(".", "aggressive", 0)
        data.cheerful   = m.getfloat(".", "cheerful",   0)
        data.brave      = m.getfloat(".", "brave",      0)
        data.cautious   = m.getfloat(".", "cautious",   0)
        data.trickish   = m.getfloat(".", "trickish",   0)
        race = self.get_race()
        data.maxdex = race.dex + 6
        data.maxagl = race.agl + 6
        data.maxint = race.int + 6
        data.maxstr = race.str + 6
        data.maxvit = race.vit + 6
        data.maxmin = race.min + 6

        cw.cwpy.setting.periods[index].demodulate(data)
        cw.cwpy.setting.periods[index + 1].modulate(data)
        cw.features.wrap_ability(data)

        p.set("dex", str(int(data.dex)))
        p.set("agl", str(int(data.agl)))
        p.set("int", str(int(data.int)))
        p.set("str", str(int(data.str)))
        p.set("vit", str(int(data.vit)))
        p.set("min", str(int(data.min)))
        m.set("aggressive", str(data.aggressive))
        m.set("cheerful",   str(data.cheerful))
        m.set("brave",      str(data.brave))
        m.set("cautious",   str(data.cautious))
        m.set("trickish",   str(data.trickish))

        for e in data.getfind("Property/Coupons"):
            if e.text <> self.age:
                continue
            # 年代クーポンを上書き
            e.text = nextage
        self.age = nextage

        data.write_xml(True)

    def get_imgpath(self):
        return cw.util.join_yadodir(self.imgpath)

    def get_age(self):
        for period in cw.cwpy.setting.periods:
            if self.age == u"＿" + period.name:
                return period.subname
        return ""

    def get_sex(self):
        for sex in cw.cwpy.setting.sexes:
            if self.sex == u"＿" + sex.name:
                return sex.subname
        return ""

    def get_race(self):
        if self.race:
            for race in cw.cwpy.setting.races:
                if race.name == self.race:
                    return race
        return cw.cwpy.setting.unknown_race

class Gene(object):
    def __init__(self, bits=[]):
        if bits:
            self.bits = bits
        else:
            self.bits = [0 for cnt in xrange(10)]

        self.count = 0

    def get_str(self):
        return "".join([str(bit) for bit in self.bits])

    def set_str(self, s, count=0):
        self.bits = [int(char) for char in s]
        self.count += count

    def set_bit(self, index, value=1):
        index = cw.util.numwrap(index, 0, 9)
        self.bits[index] = 1 if value else 0

    def set_randombit(self):
        n = cw.cwpy.dice.roll(sided=10)
        self.bits[n - 1] = 1

    def set_talentbit(self, talent, oldtalent=""):
        for nature in cw.cwpy.setting.natures:
            if u"＿" + nature.name == talent:
                for index in xrange(len(nature.genepattern)):
                    if nature.genepattern[index] == '1':
                        self.set_bit(index)
                if nature.genecount == 0:
                    self.set_talentbit(oldtalent)
                break

    def count_bits(self):
        return len([bit for bit in self.bits if bit])

    def reverse(self):
        bits = [int(not bit) for bit in self.bits]
        return Gene(bits)

    def fusion(self, gene):
        # 排他的論理和演算
        bits = [bit1 ^ bit2 for bit1, bit2 in zip(self.bits, gene.bits)]
        return Gene(bits)

    def rotate(self):
        # 母親の遺伝情報のローテート
        n = self.count % 7
        if n == 0:
            count = 3
        elif n == 1:
            count = 0
        elif n == 2:
            count = 4
        elif n == 3:
            count = 1
        elif n == 4:
            count = 5
        elif n == 5:
            count = 2
        else:
            count = 6
        bits_l = self.bits[:7]
        bits_r = self.bits[7:]
        bits = bits_l[:count]
        bits.extend(bits_l[count:])
        bits.extend(bits_r)
        return Gene(bits)

class ScenarioHeader(object):
    def __init__(self, t):
        self.dpath = t[0]
        self.type = t[1]
        self.fname = t[2]
        self.name = t[3]
        self.author = t[4]
        self.desc = t[5]
        self.skintype = t[6]
        self.levelmin = t[7]
        self.levelmax = t[8]
        self.coupons = t[9]
        self.couponsnum = t[10]
        self.startid = t[11]
        self.tags = t[12]
        self.ctime = t[13]
        self.mtime = t[14]
        self.image = t[15]
        self._wxbmp = None

    def header2tuple(self):
        return (self.dpath, self.type, self.fname, self.name, self.author, self.desc,
                self.skintype, self.levelmin, self.levelmax, self.coupons,
                self.couponsnum, self.startid, self.tags, self.ctime,
                self.mtime, self.image)

    def get_fpath(self):
        return "/".join([self.dpath, self.fname])

    def get_wxbmp(self, mask=True):
        if not self._wxbmp:
            if self.image:
                with io.BytesIO(str(self.image)) as f:
                    # TODO scaleinfo
                    self._wxbmp = cw.wins((cw.util.load_wxbmp(f=f, mask=mask), cw.SIZE_CARDIMAGE))
            else:
                self._wxbmp = wx.EmptyBitmap(cw.wins(0), cw.wins(0))
        return self._wxbmp

class PartyHeader(object):
    def __init__(self, data=None, dbrec=None):
        """
        data: PartyのPropetyElement。
        dbrec: データベースから生成する場合は対象レコード。
        """
        if dbrec:
            self.fpath = dbrec["fpath"]
            self.name = dbrec["name"]
            self.money = dbrec["money"]
            self.members = dbrec["members"].split("\n")
        else:
            self.fpath = data.fpath
            self.name = data.gettext("Name")
            self.money = data.getint("Money", 0)
            self.members = [e.text for e in data.getfind("Members") if e.text]

        self.data = None

    def is_adventuring(self):
        path = cw.util.splitext(self.fpath)[0] + ".wsl"
        return bool(cw.util.get_yadofilepath(path))

    def get_sceheader(self):
        """
        現在冒険中のシナリオのScenarioHeaderを返す。
        """
        path = cw.util.splitext(self.fpath)[0] + ".wsl"
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

    def get_memberpaths(self, yadodir=None):
        seq = []

        for fname in self.members:
            fname2 = fname + ".xml"
            if yadodir:
                path = cw.util.join_paths(yadodir, "Adventurer", fname2)
            else:
                path = cw.util.join_yadodir(cw.util.join_paths("Adventurer", fname2))
            if not os.path.isfile(path):
                # Windowsがファイル名を変えるため前後のスペースを除く
                fname2 = fname.strip() + ".xml"
                if yadodir:
                    path = cw.util.join_paths(yadodir, "Adventurer", fname2)
                else:
                    path = cw.util.join_yadodir(cw.util.join_paths("Adventurer", fname2))
            seq.append(path)

        return seq

    def get_membernames(self):
        seq = []

        for fpath in self.get_memberpaths():
            seq.append(GetName(fpath).name)

        return seq

class PartyRecordHeader(object):
    def __init__(self, fpath=None, dbrec=None, partyrecord=None):
        """
        fpath: ファイルから生成する場合はXMLファイルパス。
        dbrec: データベースから生成する場合は対象レコード。
        partyrecord: パーティ記録から生成する場合は対象記録。
        """
        if dbrec:
            self.fpath = dbrec["fpath"]
            self.name = dbrec["name"]
            self.money = dbrec["money"]
            self.members = dbrec["members"].split("\n")
            self.membernames = dbrec["membernames"].split("\n")
            if len(self.membernames) < len(self.members):
                self.membernames.extend([u""] * (len(self.members)-len(self.membernames)))
            self.backpack = dbrec["backpack"].split("\n")
        elif partyrecord:
            self.fpath = partyrecord.fpath
            self.name = partyrecord.name
            self.money = partyrecord.money
            self.members = []
            self.membernames = []
            for member in partyrecord.members:
                s = os.path.basename(member.fpath)
                s = cw.util.splitext(s)[0]
                self.members.append(s)
                self.membernames.append(member.gettext("Property/Name", u""))
            self.backpack = [header.name for header in partyrecord.backpack]
        else:
            data = cw.data.xml2etree(fpath)
            self.fpath = data.fpath
            self.name = data.gettext("Property/Name")
            self.money = data.getint("Property/Money", 0)
            self.members = []
            self.membernames = []
            for e in data.getfind("Property/Members"):
                self.members.append(e.text if e.text else "")
                self.membernames.append(e.getattr(".", "name", u""))
            self.backpack = [e.get("name", "") for e in data.getfind("BackpackRecord")]

    def rename_member(self, fpath, name):
        """メンバの改名を通知する。"""
        s = os.path.basename(fpath)
        s = cw.util.splitext(s)[0]
        if s in self.members:
            index = self.members.index(s)
            self.membernames[index] = name
            data = cw.data.xml2etree(self.fpath)
            data.edit("Property/Members/Member[%s]" % (index+1), name, "name")
            data.write_xml()

    def vanish_member(self, fpath):
        """メンバの消滅を通知する。"""
        s = os.path.basename(fpath)
        s = cw.util.splitext(s)[0]
        if s in self.members:
            index = self.members.index(s)
            self.members[index] = ""
            data = cw.data.xml2etree(self.fpath)
            ename = "Property/Members/Member[%s]" % (index+1)
            data.edit(ename, u"")

            # 互換性維持の処理
            # 過去のデータでname属性が無い場合がある
            name = data.getattr(ename, u"name", u"")
            if not name:
                name = GetName(fpath).name
                self.membernames[index] = name
                data.edit(ename, u"", u"name")

            data.write_xml()

    def get_memberpaths(self):
        seq = []

        for fname in self.members:
            if fname:
                fname2 = fname + ".xml"
                path = cw.util.join_yadodir(cw.util.join_paths("Adventurer", fname2))
                if not os.path.isfile(path):
                    # Windowsがファイル名を変えるため前後のスペースを除く
                    fname2 = fname.strip() + ".xml"
                    path = cw.util.join_yadodir(cw.util.join_paths("Adventurer", fname2))
            else:
                path = ""
            seq.append(path)

        return seq

    def get_membernames(self):
        seq = []

        for i, fpath in enumerate(self.get_memberpaths()):
            if self.membernames[i]:
                seq.append(self.membernames[i])
            elif cw.util.get_yadofilepath(fpath):
                # name情報はないが本人のデータがある
                seq.append(GetName(fpath).name)
            else:
                # name情報もなく本人も消滅済み
                # (互換性維持)
                seq.append(u"<Vanished>")

        return seq

class GetName(object):
    """XMLファイル中のProperty/Nameの内容を読む。"""
    def __init__(self, fpath, tagname="Name"):
        self.tagname = tagname
        self.name = ""
        self.stack = []

        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.character_data

        with open(fpath) as f:
            try:
                parser.ParseFile(f)
            except Exception, ex:
                pass

    def start_element(self, name, attrs):
        self.stack.append(name)

    def end_element(self, name):
        if self.stack[1:] == ["Property"]:
            raise Exception()
        if self.stack[1:] == ["Property", self.tagname]:
            raise Exception()
        self.stack.pop()

    def character_data(self, data):
        if self.stack[1:] == ["Property", self.tagname]:
            self.name += data

class GetProperty(object):
    """XMLファイル中のProperty以下の内容を読む。"""
    def __init__(self, fpath):
        self.properties = {}
        self.attrs = {}
        self.stack = []

        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.character_data

        with open(fpath) as f:
            try:
                parser.ParseFile(f)
            except Exception, ex:
                pass

    def start_element(self, name, attrs):
        self.stack.append(name)
        if 3 == len(self.stack) and self.stack[1] == "Property":
            element = self.stack[2]
            self.attrs[name] = attrs

    def end_element(self, name):
        if self.stack[1:] == ["Property"]:
            raise Exception()
        self.stack.pop()

    def character_data(self, data):
        if 2 < len(self.stack) and self.stack[1] == "Property":
            element = self.stack[2]
            if not element in self.properties:
                self.properties[element] = ""
            self.properties[element] += data

class RaceHeader(object):
    def __init__(self, data):
        self.name = data.gettext("Name", "")
        self.desc = data.gettext("Description", "")
        self.automaton = data.getbool("Feature/Type", "automaton", False)
        self.constructure = data.getbool("Feature/Type", "constructure", False)
        self.undead = data.getbool("Feature/Type", "undead", False)
        self.unholy = data.getbool("Feature/Type", "unholy", False)
        self.noeffect_weapon = data.getbool("Feature/NoEffect", "weapon", False)
        self.noeffect_magic = data.getbool("Feature/NoEffect", "magic", False)
        self.resist_fire = data.getbool("Feature/Resist", "fire", False)
        self.resist_ice = data.getbool("Feature/Resist", "ice", False)
        self.weakness_fire = data.getbool("Feature/Weakness", "fire", False)
        self.weakness_ice = data.getbool("Feature/Weakness", "ice", False)
        self.dex = data.getint("Ability/Physical", "dex", 6)
        self.agl = data.getint("Ability/Physical", "agl", 6)
        self.int = data.getint("Ability/Physical", "int", 6)
        self.str = data.getint("Ability/Physical", "str", 6)
        self.vit = data.getint("Ability/Physical", "vit", 6)
        self.min = data.getint("Ability/Physical", "min", 6)
        self.aggressive = data.getint("Ability/Mental", "aggressive", 0)
        self.cheerful = data.getint("Ability/Mental", "cheerful", 0)
        self.brave = data.getint("Ability/Mental", "brave", 0)
        self.cautious = data.getint("Ability/Mental", "cautious", 0)
        self.trickish = data.getint("Ability/Mental", "trickish", 0)
        self.avoid = data.getint("Ability/Enhance", "avoid", 0)
        self.resist = data.getint("Ability/Enhance", "resist", 0)
        self.defense = data.getint("Ability/Enhance", "defense", 0)
        self.coupons = []

        for e in data.getfind("Coupons"):
            name = e.gettext(".", "")
            value = 0
            self.coupons.append((name, value))

class UnknownRaceHeader(RaceHeader):
    def __init__(self, setting):
        self.name = setting.msgs["unknown_race_name"]
        self.desc = setting.msgs["unknown_race_description"]
        self.automaton = False
        self.constructure = False
        self.undead = False
        self.unholy = False
        self.noeffect_weapon = False
        self.noeffect_magic = False
        self.resist_fire = False
        self.resist_ice = False
        self.weakness_fire = False
        self.weakness_ice = False
        self.dex = 6
        self.agl = 6
        self.int = 6
        self.str = 6
        self.vit = 6
        self.min = 6
        self.aggressive = 0
        self.cheerful = 0
        self.brave = 0
        self.cautious = 0
        self.trickish = 0
        self.avoid = 0
        self.resist = 0
        self.defense = 0
        self.coupons = []

def main():
    pass

if __name__ == "__main__":
    main()
