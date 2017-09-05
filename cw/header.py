#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import sys
import re
import copy
import weakref
import subprocess
import wx
import pygame
import xml.parsers.expat
import shutil
import math

import cw


def to_imgpaths(dbrec, imgdbrec):
    """1枚イメージの情報を持つDBレコードと
    複数イメージの情報を持つDBレコードを元に
    cw.image.ImageInfoのlistを生成する。
    """
    imgpaths = []
    path = dbrec["imgpath"]
    postype = dbrec["postype"] if "postype" in dbrec else "Default"
    if postype is None:
        postype = "Default"
    if path:
        imgpaths.append(cw.image.ImageInfo(path, postype=postype))
    if imgdbrec:
        for imgrec in imgdbrec:
            postype = imgrec["postype"] if "postype" in imgrec.keys() else "Default"
            if postype is None:
                postype = "Default"
            imgpaths.append(cw.image.ImageInfo(imgrec["imgpath"], postype=postype))
    return imgpaths

class CardHeader(object):
    def __init__(self, data=None, owner=None, carddata=None, from_scenario=False, scedir="", put_db=False, dbrec=None, imgdbrec=None, dbowner="STOREHOUSE", bgtype=""):
        self.ref_original = weakref.ref(self)
        self.order = -1
        if dbrec:
            self.set_owner(dbowner)
            self.carddata = None
            self.fpath = dbrec["fpath"]
            self.type = dbrec["type"]
            self.id = dbrec["id"]
            self.name = dbrec["name"]
            self.imgpaths = to_imgpaths(dbrec, imgdbrec)
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
            self.wsnversion = dbrec["wsnversion"] # ""の場合はWsn.1以前
            if not self.wsnversion:
                self.wsnversion = ""
            self.moved = dbrec["moved"]
            self.star = dbrec["star"]
        else:
            self.set_owner(owner)
            self.carddata = carddata
            self.wsnversion = carddata.getattr(".", "dataVersion", "")

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
            self.imgpaths = cw.image.get_imageinfos(data)
            # 互換性マーク
            self.versionhint = cw.cwpy.sct.from_basehint(data.getattr(".", "versionHint", ""))

        self.bgtype = bgtype

        self.vocation = (self.physical, self.mental)

        self._cardscale = cw.UP_SCR
        self._wxcardscale = cw.UP_WIN
        self._skindirname = cw.cwpy.setting.skindirname
        self._bordering_cardname = cw.cwpy.setting.bordering_cardname
        self._show_premiumicon = cw.cwpy.setting.show_premiumicon

        # スキルカードと召喚獣カードは価格固定
        if self.type == "SkillCard":
            self.price = 400 + self.level * 200
        elif self.type == "BeastCard":
            self.price = 1000

        # シナリオ取得フラグ
        scenariocard = not (self.carddata is None) and self.carddata.getbool(".", "scenariocard", False)
        if from_scenario or (self.carddata is not None) and scenariocard:
            self.scenariocard = True
            if scedir:
                self.scedir = scedir
            else:
                self.scedir = cw.cwpy.sdata.scedir
        else:
            self.scenariocard = False
            self.scedir = scedir
        # 画像設定
        self._cardimg = None
        self.rect = cw.s(pygame.Rect(0, 0, 80, 110))
        self.wxrect = cw.wins(pygame.Rect(0, 0, 80, 110))
        # cardcontrolダイアログで使うフラグ
        self.negaflag = False
        self.clickedflag = False

        # 特殊なキーコード
        self.penalty = bool(cw.cwpy.msgs["penalty_keycode"] in self.keycodes)
        if not scenariocard and self.type == "BeastCard" and isinstance(owner, (cw.character.Friend, cw.character.Enemy)):
            # 最初から持っていた使用回数ありリサイクル召喚獣に限っては
            # 付帯能力でなくてもリサイクル状態が有効になる
            reattachment = True
        else:
            reattachment = (self.attachment or self.type == "ItemCard")
        self.recycle = bool(self.type in ("ItemCard", "BeastCard") and cw.cwpy.msgs["recycle_keycode"] in self.keycodes and reattachment)
        self.keycodes.append(self.name)

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

        # 遅延書き込み
        self._lazy_write = None

    @property
    def negastar(self):
        if self.star is None:
            return 0
        return -self.star

    def set_cardimg(self, imgpaths, can_loaded_scaledimage, anotherscenariocard):
        paths = []
        for info in imgpaths:
            path = info.path
            if not cw.binary.image.path_is_code(path):
                if self.type in ("ActionCard", "UseCardInBackpack"):
                    path = cw.util.join_paths(cw.cwpy.skindir, path)
                    path = cw.util.get_materialpathfromskin(path, cw.M_IMG)
                elif anotherscenariocard:
                    path = cw.util.join_yadodir(path)
                elif self.scenariocard or self.scedir:
                    path = path
                elif not self.scenariocard:
                    path = cw.util.join_yadodir(path)
            paths.append(cw.image.ImageInfo(path, base=info))

        self._cardimg = cw.image.CardImage(paths, self.get_bgtype(), self.name, self.premium,
                                           can_loaded_scaledimage=can_loaded_scaledimage, is_scenariocard=self.scenariocard,
                                           anotherscenariocard=anotherscenariocard, scedir=self.scedir)
        self.rect = pygame.Rect(self.rect)
        self.rect.size = self._cardimg.rect.size
        self.wxrect = pygame.Rect(self._cardimg.wxrect)
        self._cardscale = cw.UP_SCR
        self._wxcardscale = cw.UP_WIN
        self._skindirname = cw.cwpy.setting.skindirname
        self._bordering_cardname = cw.cwpy.setting.bordering_cardname
        self._show_premiumicon = cw.cwpy.setting.show_premiumicon

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
                self._skindirname <> cw.cwpy.setting.skindirname or\
                self._bordering_cardname <> cw.cwpy.setting.bordering_cardname or\
                self._show_premiumicon <> cw.cwpy.setting.show_premiumicon:
            if self.carddata is None:
                rootattrs = GetRootAttribute(self.fpath)
                can_loaded_scaledimage = cw.util.str2bool(rootattrs.attrs.get("scaledimage", "False"))
                anotherscenariocard = cw.util.str2bool(rootattrs.attrs.get("anotherscenariocard", "False"))
            else:
                can_loaded_scaledimage = self.carddata.getbool(".", "scaledimage", False)
                anotherscenariocard = self.carddata.getbool(".", "anotherscenariocard", False)
            self.set_cardimg(self.imgpaths, can_loaded_scaledimage, anotherscenariocard)
        return self._cardimg

    def get_cardwxbmp(self, test_aptitude=None):
        return self.cardimg.get_cardwxbmp(self, test_aptitude=test_aptitude)

    def get_cardimg(self):
        return self.cardimg.get_cardimg(self)

    def do_write(self, dupcheck=True):
        if not self._lazy_write is None:
            if dupcheck:
                self._lazy_write.fpath = cw.util.dupcheck_plus(self._lazy_write.fpath)
            self._lazy_write.write_xml(True)
            self.fpath = self._lazy_write.fpath
            self._lazy_write = None

            # self.fpathを削除予定のfpathリストから削除
            cw.cwpy.ydata.deletedpaths.discard(self.fpath)

    def get_vocation_level(self, owner, enhance_act=False):
        """
        適性値の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
        enhance_act : 行動力を加味する場合、True
        """
        return cw.effectmotion.get_vocation_level(owner, self.vocation, enhance_act=enhance_act)

    def get_showed_vocation_level(self, owner):
        """
        表示される適性値の段階値を返す。値は0～3の範囲となる。
        1.20相当の計算を行う時は、実際の能力値と厳密には一致しない。
        """
        if cw.cwpy.setting.vocation120:
            # スキンによる互換機能
            # 1.20相当の適性計算を行う
            value = self.get_vocation_val(owner, enhance_act=False)
            if value < 4:
                value = 0
            elif value < 8:
                value = 1
            elif value < 12:
                value = 2
            else:
                value = 3
            return value
        else:
            return min(3, self.get_vocation_level(owner, enhance_act=False))

    def get_vocation_val(self, owner, enhance_act=False):
        """
        適性値(身体特性+精神特性の合計値)を返す。
        enhance_act : 行動力を加味する場合、True
        """
        if not owner:
            owner = self.get_owner()
        return cw.effectmotion.get_vocation_val(owner, self.vocation, enhance_act=enhance_act)

    def get_uselimit_level(self):
        """
        使用回数の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
        """
        limit, maxlimit = self.get_uselimit()
        if maxlimit <= 0:
            return 0
        limitper = 100 * limit / maxlimit

        if maxlimit <= limit:
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

    def set_uselimit(self, value, animate=False):
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
            if owner:
                owner.data.is_edited = True
                if owner.deck:
                    owner.deck.update_skillcardimage(header)
        # アイテムカード。
        elif header.type == "ItemCard" and not header.maxuselimit == 0:
            header.uselimit += value
            header.uselimit = cw.util.numwrap(header.uselimit, 0, 999)
            e = header.carddata.getfind("Property/UseLimit")
            e.text = str(header.uselimit)
            if owner:
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
            if owner:
                owner.data.is_edited = True

                # カード消滅処理
                if header.uselimit <= 0 and not header.recycle and header.get_owner() == owner:
                    # 召喚獣消去効果で消えてる場合もあるのでチェック
                    if header in owner.cardpocket[cw.POCKET_BEAST] and header.get_owner() == owner:
                        if not animate or owner.status == "hidden":
                            cw.cwpy.trade("TRASHBOX", header=header, from_event=True, clearinusecard=False)
                        else:
                            cw.animation.animate_sprite(owner, "hide", battlespeed=cw.cwpy.is_battlestatus())
                            cw.cwpy.trade("TRASHBOX", header=header, from_event=True, clearinusecard=False)
                            cw.animation.animate_sprite(owner, "deal", battlespeed=cw.cwpy.is_battlestatus())

    def write(self, party=None, move=False, from_getcontent=False):
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
                dupcheck = False
            else:
                path = create_newpath(party)
                self.fpath = path
                dupcheck = True

            etree = cw.data.xml2etree(element=self.carddata)
            etree.fpath = self.fpath

            if not from_getcontent and not self.type == "BeastCard":
                etree.edit("Property/Hold", "False")

            self._lazy_write = etree
            if not from_getcontent or not self.scenariocard:
                self.do_write(dupcheck=dupcheck)

    def contain_xml(self, load=True):
        if not load and not self._lazy_write is None:
            return
        if self.carddata is None:
            if load:
                self.do_write()
                e = cw.data.yadoxml2etree(self.fpath)
                self.carddata = e.getroot()
            if self._lazy_write is None:
                # self.fpathを削除予定のfpathリストに追加
                cw.cwpy.ydata.deletedpaths.add(self.fpath, self.scenariocard)

    def remove_importedmaterials(self):
        # 取り込み素材をフォルダごと削除
        if self.carddata is None:
            self.do_write()
            self.carddata = cw.data.yadoxml2element(self.fpath)

        emp = self.carddata.find("Property/Materials")
        if not emp is None:
            mates = cw.util.join_yadodir(emp.text)
            cw.cwpy.ydata.deletedpaths.add(mates, True)

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
            imgpaths = cw.image.get_imageinfos(self.carddata.find("Property"))
            self.set_cardimg(imgpaths, can_loaded_scaledimage=self.carddata.getbool(".", "scaledimage", False),
                             anotherscenariocard=self.carddata.getbool(".", "anotherscenariocard", False))

    def set_scenarioend(self):
        """
        シナリオ終了時に呼ばれる。
        非付帯召喚カードを削除したり、
        シナリオで取得したカードの素材ファイルを宿にコピーしたりする。
        """
        self.do_write()
        if self.scenariocard:
            if self.carddata is None:
                assert self.fpath, self.name
                assert os.path.isfile(self.fpath), self.fpath
                self.carddata = cw.data.xml2element(self.fpath)

            # シナリオ取得フラグクリア
            self.scenariocard = False
            self.scedir = ""
            if "scenariocard" in self.carddata.attrib:
                self.carddata.attrib.pop("scenariocard")
            if "anotherscenariocard" in self.carddata.attrib:
                self.carddata.attrib.pop("anotherscenariocard")
            # 画像コピー
            dstdir = cw.util.join_paths(cw.cwpy.yadodir,
                                            "Material", self.type, self.name if self.name else "noname")
            dstdir = cw.util.dupcheck_plus(dstdir)
            can_loaded_scaledimage = self.carddata.getbool(".", "scaledimage", False)
            cw.cwpy.copy_materials(self.carddata, dstdir, can_loaded_scaledimage=can_loaded_scaledimage)
            # 画像更新
            self.imgpaths = cw.image.get_imageinfos(self.carddata.find("Property"))
            self.set_cardimg(self.imgpaths, can_loaded_scaledimage=self.carddata.getbool(".", "scaledimage", False),
                             anotherscenariocard=False)
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
        header.set_cardimg(self.imgpaths, can_loaded_scaledimage=self.carddata.getbool(".", "scaledimage", False),
                           anotherscenariocard=self.carddata.getbool(".", "anotherscenariocard", False))
        return header

    def is_ccardheader(self):
        return bool(isinstance(self._owner, weakref.ref))

    def is_backpackheader(self):
        return bool(self._owner == "BACKPACK")

    def is_storehouseheader(self):
        return bool(self._owner == "STOREHOUSE")

    def is_hold(self):
        if self.type == "SkillCard":
            pocket = cw.POCKET_SKILL
        elif self.type == "ItemCard":
            pocket = cw.POCKET_ITEM
        elif self.type == "BeastCard":
            pocket = cw.POCKET_BEAST
        else:
            pocket = -1

        if pocket <> -1:
            owner = self.get_owner()
            if (self.hold or (owner and owner.hold_all[pocket])) and not self.penalty and self.type <> "BeastCard":
                # ホールド(ペナルティカード以外)
                return True
        return False

    def is_autoselectable(self):
        card = self.ref_original()

        if card.recycle and card.uselimit <= 0:
            # 使用回数0(リサイクルカードのみ)
            return False

        if card.is_hold():
            # ホールド(ペナルティカード以外)
            return False

        # 対象無しまたは効果無し
        noeffect = bool(card.target == "None")
        if not card.carddata is None:
            noeffect |= card.carddata.find("Motions/Motion") is None

        owner = card.get_owner()
        silence = False
        if not card.carddata is None and owner:
            # 沈黙
            spell = card.carddata.getbool("Property/EffectType", "spell", False)
            silence |= owner.is_silence() and spell

            if card.type <> "BeastCard":
                # 魔法無効状態
                effecttype = card.carddata.gettext("Property/EffectType", "")
                magic = effecttype in ("Magic", "PhysicalMagic")
                silence |= owner.is_antimagic() and magic

        if not silence:
            # 使用時ボーナス・ペナルティがあるカードは効果がなくても選択可能
            # ただしCardWirthでは沈黙・魔法無効化の影響は受ける
            if card.enhance_avo_used <> 0 or\
               card.enhance_res_used <> 0 or\
               card.enhance_def_used <> 0:
                return True

        return not (noeffect or silence)

    def get_targets(self):
        """
        (ターゲットのリスト,
         効果のあるターゲットのリスト,
         優先すべきターゲットのリスト)
        を返す。
        """
        owner = self.get_owner()

        if self.target == "Both":
            if isinstance(owner, cw.character.Enemy):
                targets = cw.cwpy.get_ecards("unreversed")[:]
                targets.extend(cw.cwpy.get_pcards("unreversed"))
            else:
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

        effective = cw.effectmotion.get_effectivetargets(self, targets)
        return targets, effective

    def is_noeffect(self, target):
        effecttype = self.carddata.gettext("Property/EffectType", "")
        if cw.effectmotion.check_noeffect(effecttype, target):
            return True
        for e in self.carddata.getfind("Motions"):
            element = e.getattr(".", "element", "")
            if not cw.effectmotion.is_noeffect(element, target):
                return False
        return True

    def get_keycodes(self, with_name=True):
        if not with_name:
            return self.keycodes[:-1]

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
        self.do_write()
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

    @property
    def sellingprice(self):
        """カードの売却価格。"""
        # 互換動作: 1.30以前ではカードの売値は常に半額
        if cw.cwpy.sct.lessthan("1.30", self.versionhint):
            price = self.price // 2
        elif self.premium == "Normal":
            price = self.price // 2
        else:
            price = int(self.price * 0.75)

        if self.type == "ItemCard" and 0 < self.maxuselimit:
            # 使用回数がある場合は使うほど売値が減る
            price = price * self.uselimit // self.maxuselimit

        return price

    def can_selling(self):
        """売却可能か？"""
        # プレミアカードは売却・破棄できない(イベントからの呼出以外)
        if not cw.cwpy.debug and cw.cwpy.setting.protect_premiercard and\
                self.premium == "Premium":
            return False

        # スターつきのカードは売却・破棄できない(イベントからの呼出以外)
        if cw.cwpy.setting.protect_staredcard and self.star:
            return False

        return True

class InfoCardHeader(object):
    def __init__(self, data, can_loaded_scaledimage):
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
        imgpaths = cw.image.get_imageinfos(data)
        self.imgpaths = imgpaths
        self.can_loaded_scaledimage = can_loaded_scaledimage
        self.set_cardimg(self.can_loaded_scaledimage, False)
        # cardcontrolダイアログで使うフラグ
        self.negaflag = False
        self.clickedflag = False

    def set_cardimg(self, can_loaded_scaledimage, anotherscenariocard):
        self.can_loaded_scaledimage = can_loaded_scaledimage
        self.anotherscenariocard = anotherscenariocard
        self._cardimg = cw.image.CardImage(self.imgpaths, "INFO", self.name,
                                           can_loaded_scaledimage=can_loaded_scaledimage, is_scenariocard=True,
                                           anotherscenariocard=anotherscenariocard)
        self.rect = self._cardimg.rect
        self.wxrect = self._cardimg.wxrect
        self._cardscale = cw.UP_SCR
        self._wxcardscale = cw.UP_WIN
        self._skindirname = cw.cwpy.setting.skindirname
        self._bordering_cardname = cw.cwpy.setting.bordering_cardname

    @property
    def cardimg(self):
        if self._cardscale <> cw.UP_SCR or\
                self._wxcardscale <> cw.UP_WIN or\
                self._skindirname <> cw.cwpy.setting.skindirname or\
                self._bordering_cardname <> cw.cwpy.setting.bordering_cardname:
            self.set_cardimg(self.can_loaded_scaledimage, False)
        return self._cardimg

    def get_cardwxbmp(self, test_aptitude=None):
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
    def __init__(self, data=None, album=False, dbrec=None, imgdbrec=None, fpath="", rootattrs=None):
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
            self.desc = dbrec["desc"]
            self.imgpaths = to_imgpaths(dbrec, imgdbrec)
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
            # ""の場合はWsn.1以前
            self.wsnversion = dbrec["wsnversion"]
            if not self.wsnversion:
                self.wsnversion = ""

        elif fpath:
            self.fpath = fpath
            prop = GetProperty(fpath)
            self.level = cw.util.numwrap(int(prop.properties.get("Level", "1")), 1, 65536)
            self.name = prop.properties.get("Name", "")
            self.desc = cw.util.decodewrap(prop.properties.get("Description", ""))
            self.imgpaths = cw.image.get_imageinfos_p(prop)
            self.album = album
            self.lost = cw.util.str2bool(prop.attrs.get(".", {}).get("lost", "False"))

            ages = set(cw.cwpy.setting.periodcoupons)
            sexs = set(cw.cwpy.setting.sexcoupons)
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
            self.versionhint = cw.cwpy.sct.from_basehint(prop.attrs.get(".", {}).get("versionHint", ""))
            self.wsnversion = prop.attrs.get(None, {}).get("dataVersion", "")

            for _coupon, attrs, name in reversed(prop.third.get("Coupons", [])):
                if not name:
                    continue
                elif name in ages:
                    self.age = name
                elif name in sexs:
                    self.sex = name
                elif name == u"＠ＥＰ":
                    self.ep = int(attrs.get("value", 0))
                elif name == u"＿消滅予約":
                    self.leavenoalbum = True
                elif r_gene.match(name):
                    self.gene.set_str(name[2:], int(attrs.get("value", 0)))
                elif name.startswith(u"＠Ｒ"):
                    self.race = name[2:]

                self.history.append(name)

        else:
            self.fpath = data.fpath
            self.level = cw.util.numwrap(data.getint("Level", 1), 1, 65536)
            self.name = data.gettext("Name", "")
            self.desc = cw.util.decodewrap(data.gettext("Description", ""))
            self.imgpaths = cw.image.get_imageinfos(data)
            self.album = album

            # シナリオプレイ中にロストしたかどうかのフラグ
            if data.hasfind(".", "lost"):
                self.lost = True
            else:
                self.lost = False

            # クーポンにある各種変数取得
            ages = set(cw.cwpy.setting.periodcoupons)
            sexs = set(cw.cwpy.setting.sexcoupons)
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
            self.wsnversion = rootattrs.get("dataVersion", "") if rootattrs else ""

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

                self.history.append(e.text)

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

        ep = False
        gene = False
        for e in data.find("Property/Coupons"):
            if ep and gene:
                break
            if not e.text:
                continue

            # EP減少
            if e.text == u"＠ＥＰ" and not ep:
                e.attrib["value"] = str(e.getint(".", "value") - n)
                ep = True
            # 子作り回数加算
            elif r_gene.match(e.text) and not gene:
                self.gene.count = e.getint(".", "value") + 1
                e.attrib["value"] = str(self.gene.count)
                gene = True

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

        # 能力値を再調整。ただし精神傾向は変化しない
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

        cw.cwpy.setting.periods[index].demodulate(data, mental=False)
        cw.cwpy.setting.periods[index + 1].modulate(data, mental=False)
        cw.features.wrap_ability(data)

        p.set("dex", str(int(data.dex)))
        p.set("agl", str(int(data.agl)))
        p.set("int", str(int(data.int)))
        p.set("str", str(int(data.str)))
        p.set("vit", str(int(data.vit)))
        p.set("min", str(int(data.min)))

        for e in data.getfind("Property/Coupons"):
            if e.text <> self.age:
                continue
            # 年代クーポンを上書き
            e.text = nextage
        self.age = nextage

        data.write_xml(True)

    def get_imgpaths(self):
        seq = []
        for info in self.imgpaths:
            seq.append(cw.image.ImageInfo(cw.util.join_yadodir(info.path), base=info))
        return seq

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
    def __init__(self, bits=[][:], count=0):
        if bits:
            self.bits = bits
        else:
            self.bits = [0 for _cnt in xrange(10)]

        self.count = count

    def get_str(self):
        return "".join([str(bit) for bit in self.bits])

    def set_str(self, s, count=0):
        self.bits = [int(char) for char in s]
        self.count = count

    def reverse_bit(self, index):
        if 0 <= index < 10:
            self.bits[index] = 0 if self.bits[index] else 1

    def set_bit(self, index, value):
        if 0 <= index < 10:
            self.bits[index] = 1 if value else 0

    def set_randombit(self):
        n = cw.cwpy.dice.roll(sided=10)
        self.bits[n - 1] = 1

    def set_talentbit(self, talent, oldtalent=""):
        for nature in cw.cwpy.setting.natures:
            if u"＿" + nature.name == talent:
                # 型に対応する型のbitを1にする
                for index in xrange(len(nature.genepattern)):
                    if nature.genepattern[index] == '1':
                        self.set_bit(index, 1)
                if nature.genecount == 0:
                    # 最弱遺伝子型(凡庸)
                    # 選択した型のbitも1にする
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

    def rotate_father(self):
        # 父親の遺伝情報のローテート(左へ)
        count = (self.count-1) % 10
        bits = self.bits[count:]
        bits.extend(self.bits[:count])
        return Gene(bits)

    def rotate_mother(self):
        # 母親の遺伝情報のローテート(右へ)
        count = (10 - (self.count-1)%10) % 10
        bits = self.bits[count:]
        bits.extend(self.bits[:count])
        return Gene(bits)

assert Gene([0, 1, 1, 0, 1, 0, 1, 0, 1, 1], 4).rotate_father().get_str() == "0101011011"
assert Gene([0, 1, 1, 0, 0, 0, 0, 0, 0, 1], 3).rotate_mother().get_str() == "0101100000"


class ScenarioHeader(object):
    def __init__(self, dbrec, imgdbrec):
        self.dpath = dbrec["dpath"]
        self.type = dbrec["type"]
        self.fname = dbrec["fname"]
        self.name = dbrec["name"]
        self.author = dbrec["author"]
        self.desc = dbrec["desc"]
        self.skintype = dbrec["skintype"]
        self.levelmin = dbrec["levelmin"]
        self.levelmax = dbrec["levelmax"]
        self.coupons = dbrec["coupons"]
        self.couponsnum = dbrec["couponsnum"]
        self.startid = dbrec["startid"]
        self.tags = dbrec["tags"]
        self.ctime = dbrec["ctime"]
        self.mtime = dbrec["mtime"]
        # ""の場合はWsn.1以前
        self.wsnversion = dbrec["wsnversion"]
        if not self.wsnversion:
            self.wsnversion = ""
        self.images = { 1: [] }
        self.imgpaths = []

        image = dbrec["image"]
        imgpath = dbrec["imgpath"]
        if image or imgpath:
            self.images[1] = [image]
            self.imgpaths.append(cw.image.ImageInfo(path=imgpath if imgpath else ""))
        if imgdbrec:
            for imgrec in imgdbrec:
                scale = imgrec["scale"]
                if scale in self.images:
                    seq = self.images[scale]
                else:
                    seq = []
                    self.images[scale] = seq
                seq.append(imgrec["image"])
                postype = imgrec["postype"]
                if not postype:
                    postype = "Default"
                imgpath = imgrec["imgpath"]
                if not imgpath:
                    imgpath = ""
                self.imgpaths.append(cw.image.ImageInfo(path=imgpath, postype=postype))

        self._wxbmps = None
        self._wxbmps_noscale = None
        self.skindir = None
        self._up_win = None
        self._up_scr = None

    @property
    def mtime_reversed(self):
        """整列用の逆転した変更日時。"""
        return -self.mtime

    def get_fpath(self):
        return "/".join([self.dpath, self.fname])

    def get_wxbmps(self, mask=True):
        if self._wxbmps is None or self.skindir <> cw.cwpy.skindir or self._up_win <> cw.UP_WIN or self._up_scr <> cw.UP_SCR:
            self.skindir = cw.cwpy.skindir
            self._up_win = cw.UP_WIN
            self._up_scr = cw.UP_SCR
            self._wxbmps = []
            self._wxbmps_noscale = []

            images = self.images[1]
            imagesx1 = images
            scale = int(math.pow(2, int(math.log(cw.UP_SCR, 2))))
            while 2 <= scale:
                if scale in self.images:
                    images = self.images[scale]
                    break
                scale /= 2

            for image, imagex1, info in zip(images, imagesx1, self.imgpaths):
                if image:
                    with io.BytesIO(str(imagex1)) as f:
                        bmp_noscale = cw.util.load_wxbmp(f=f, mask=mask)
                        bmp_noscale.scr_scale = 1
                        f.close()
                    if scale == 1:
                        bmp = cw.wins(bmp_noscale)
                    else:
                        with io.BytesIO(str(image)) as f:
                            bmp = cw.util.load_wxbmp(f=f, mask=mask)
                            bmp.scr_scale = scale
                            f.close()
                        bmp = cw.wins(bmp)
                    self._wxbmps_noscale.append(bmp_noscale)
                    self._wxbmps.append(bmp)
                elif info.path:
                    # スキンのTableフォルダを指定している場合はDBにバイナリが無い
                    path = cw.util.get_materialpathfromskin(info.path, cw.M_IMG)
                    if path:
                        bmp = cw.util.load_wxbmp(path, mask=mask, noscale=True)
                        self._wxbmps_noscale.append(bmp)
                        if not cw.UP_SCR == 1:
                            bmp = cw.util.load_wxbmp(path, mask=mask, can_loaded_scaledimage=True)
                        self._wxbmps.append(cw.wins(bmp))

        return self._wxbmps, self._wxbmps_noscale

class PartyHeader(object):
    def __init__(self, data=None, dbrec=None):
        """
        data: PartyのPropetyElement。
        dbrec: データベースから生成する場合は対象レコード。
        """
        self.order = -1
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
        self._memberprops = None
        self._membernames = None
        self._memberdescs = None
        self._membercoupons = None
        self._memberlevels = None

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

    def _get_properties(self):
        if self._memberprops is None:
            self._memberprops = []
            for fpath in self.get_memberpaths():
                self._memberprops.append(GetProperty(fpath))
        return self._memberprops

    def get_membernames(self):
        if self._membernames is None:
            self._membernames = []
            for prop in self._get_properties():
                self._membernames.append(prop.properties.get("Name", u""))
        return self._membernames

    def get_memberdescs(self):
        if self._memberdescs is None:
            self._memberdescs = []
            for prop in self._get_properties():
                self._memberdescs.append(prop.properties.get("Description", u""))
        return self._memberdescs

    def get_membercoupons(self):
        if self._membercoupons is None:
            self._membercoupons = []
            for prop in self._get_properties():
                coupons = []
                for _coupon, attrs, name in reversed(prop.third.get("Coupons", [])):
                    if not name:
                        continue
                    coupons.append(name)
                self._membercoupons.append(coupons)
        return self._membercoupons

    def get_memberlevels(self):
        if self._memberlevels is None:
            self._memberlevels = []
            for prop in self._get_properties():
                self._memberlevels.append(int(prop.properties.get("Level", u"1")))
        return self._memberlevels

    @property
    def average_level(self):
        levels = self.get_memberlevels()
        return float(sum(levels))/len(levels) if len(levels) else 1

    @property
    def highest_level(self):
        return max(self.get_memberlevels())


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

class SavedJPDCImageHeader(object):
    """保存済みJPDCイメージ。
    宿・シナリオごとにJPDCで生成されたファイルを保存する。
    """
    def __init__(self, fpath=None, dbrec=None):
        """
        fpath: ファイルから生成する場合はXMLファイルパス。
        dbrec: データベースから生成する場合は対象レコード。
        savedjpdcimage: 保存済みJPDC情報から生成する場合は対象情報。
        """
        if dbrec:
            self.fpath = dbrec["fpath"]
            self.scenarioname = dbrec["scenarioname"]
            self.scenarioauthor = dbrec["scenarioauthor"]
            self.dpath = dbrec["dpath"]
            self.fpaths = dbrec["fpaths"].split("\n")
        elif fpath:
            self.fpath = fpath
            data = cw.data.xml2etree(fpath)
            self.scenarioname = data.gettext("Property/ScenarioName", u"")
            self.scenarioauthor = data.gettext("Property/ScenarioAuthor", u"")
            self.dpath = data.getattr("Materials", "dpath", "")
            self.fpaths = []
            if self.dpath:
                for e in data.getfind("Materials"):
                    if e.text:
                        self.fpaths.append(e.text)

    @staticmethod
    def create_header(debuglog):
        """シナリオ終了時にTempFileにある保存済みJPDCイメージを
        <Yado>/SavedJPDCImageに保存する。
        """
        cw.cwpy.ydata.changed()
        savedjpdcimage = cw.util.join_paths(cw.cwpy.tempdir, u"SavedJPDCImage")
        tempfilepath = cw.util.join_paths(cw.tempdir, u"ScenarioLog/TempFile")

        # ヘッダを構築
        key = (cw.cwpy.sdata.name, cw.cwpy.sdata.author)
        header = cw.cwpy.ydata.savedjpdcimage.get(key, None)
        if header:
            header.remove_all()
        else:
            header = cw.header.SavedJPDCImageHeader()
            header.dpath = cw.util.join_paths(savedjpdcimage, cw.util.repl_dischar(cw.cwpy.sdata.name))
            header.dpath = cw.util.dupcheck_plus(header.dpath)
            header.dpath = cw.util.relpath(header.dpath, savedjpdcimage)
            header.scenarioname = cw.cwpy.sdata.name
            header.scenarioauthor = cw.cwpy.sdata.author
        header.fpaths = []

        sdpath = cw.util.join_paths(savedjpdcimage, header.dpath)
        if os.path.isdir(tempfilepath):
            # TempFileのファイルをSavedJPDCImageへコピーする
            for dpath, dnames, fnames in os.walk(tempfilepath):
                for fname in fnames:
                    frompath = cw.util.join_paths(dpath, fname)
                    if not os.path.isfile(frompath):
                        continue
                    relpathbase = cw.util.relpath(frompath, tempfilepath)
                    relpath = cw.util.join_paths(u"Materials", relpathbase)
                    topath = cw.util.join_paths(sdpath, relpath)
                    dpath2 = os.path.dirname(topath)

                    if not os.path.isdir(dpath2):
                        os.makedirs(dpath2)
                    shutil.copy2(frompath, topath)
                    header.fpaths.append(relpathbase)
                    cw.cwpy.ydata.deletedpaths.discard(topath)

        if header.fpaths:
            # 情報ファイル作成
            fpath = cw.util.join_paths(sdpath, u"SavedJPDCImage.xml")
            element = cw.data.make_element("SavedJPDCImage")
            prop = cw.data.make_element("Property", u"")
            e = cw.data.make_element("ScenarioName", cw.cwpy.sdata.name)
            prop.append(e)
            e = cw.data.make_element("ScenarioAuthor", cw.cwpy.sdata.author)
            prop.append(e)
            element.append(prop)
            mates = cw.data.make_element("Materials", u"", attrs={"dpath": header.dpath})
            for mfpath in header.fpaths:
                e = cw.data.make_element("Material", mfpath)
                mates.append(e)
                if debuglog:
                    debuglog.add_jpdcimage(mfpath)
            element.append(mates)
            # ファイル書き込み
            etree = cw.data.xml2etree(element=element)
            etree.write(fpath)
            cw.cwpy.ydata.deletedpaths.discard(fpath)
            header.fpath = fpath

            cw.cwpy.ydata.savedjpdcimage[key] = header

        elif key in cw.cwpy.ydata.savedjpdcimage:
            # 保存された素材がない場合は削除
            del cw.cwpy.ydata.savedjpdcimage[key]

        return header

    def remove_all(self):
        """このオブジェクトで管理中の
        保存済みJPDCイメージを全て削除する。
        """
        cw.cwpy.ydata.changed()
        dpath1 = cw.util.join_paths(cw.cwpy.yadodir, u"SavedJPDCImage", self.dpath)
        dpath2 = cw.util.join_paths(cw.cwpy.tempdir, u"SavedJPDCImage", self.dpath)
        for dpath3 in (dpath1, dpath2):
            if os.path.isdir(dpath3):
                for dpath, dnames, fnames in os.walk(dpath3):
                    for fname in fnames:
                        fpath = cw.util.join_paths(dpath, fname)
                        if os.path.isfile(fpath):
                            cw.cwpy.ydata.deletedpaths.add(fpath)

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

        with open(fpath, "r") as f:
            try:
                parser.ParseFile(f)
            except Exception:
                pass
            f.close()

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
        self.third = {}

        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.character_data

        with open(fpath, "r") as f:
            try:
                parser.ParseFile(f)
            except Exception:
                pass
            f.close()

    def start_element(self, name, attrs):
        if 0 == len(self.stack):
            # ルート要素の属性
            self.attrs[None] = attrs

        self.stack.append(name)
        if 4 == len(self.stack) and self.stack[1] == "Property":
            name2 = self.stack[2]
            seq = self.third.get(name2, [])
            seq.append((name, attrs, ""))
            self.third[name2] = seq
        elif 3 == len(self.stack) and self.stack[1] == "Property":
            self.attrs[name] = attrs
        elif 2 == len(self.stack) and name == "Property":
            self.attrs["."] = attrs

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
            if 4 == len(self.stack):
                seq = self.third[self.stack[2]]
                seq[-1] = (seq[-1][0], seq[-1][1], seq[-1][2] + data)

class GetRootAttribute(object):
    def __init__(self, fpath):
        """XMLファイル中のルート要素の属性を読む。"""
        self.attrs = {}
        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = self.start_element

        with open(fpath, "r") as f:
            try:
                parser.ParseFile(f)
            except Exception:
                pass
            f.close()

    def start_element(self, name, attrs):
        # ルート要素の属性
        self.attrs = attrs
        raise Exception()

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
        self.aggressive = data.getfloat("Ability/Mental", "aggressive", 0.0)
        self.cheerful = data.getfloat("Ability/Mental", "cheerful", 0.0)
        self.brave = data.getfloat("Ability/Mental", "brave", 0.0)
        self.cautious = data.getfloat("Ability/Mental", "cautious", 0.0)
        self.trickish = data.getfloat("Ability/Mental", "trickish", 0.0)
        self.avoid = data.getint("Ability/Enhance", "avoid", 0)
        self.resist = data.getint("Ability/Enhance", "resist", 0)
        self.defense = data.getint("Ability/Enhance", "defense", 0)
        self.coupons = []

        for e in data.getfind("Coupons"):
            name = e.gettext(".", "")
            value = e.getint(".", "value", 0)
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
