#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import re
import copy
import weakref
import pygame
import xml.parsers.expat
import shutil
import math
import sqlite3

import cw

import wx

from typing import BinaryIO, Callable, Union, Optional, Dict, List, Tuple


def to_imgpaths(dbrec: sqlite3.Row, imgdbrec: Optional[sqlite3.Cursor]) -> List["cw.image.ImageInfo"]:
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
            postype = imgrec["postype"] if "postype" in list(imgrec.keys()) else "Default"
            if postype is None:
                postype = "Default"
            imgpaths.append(cw.image.ImageInfo(imgrec["imgpath"], postype=postype))
    return imgpaths


def cardtype_to_pocket(ctype: str) -> int:
    if ctype == "SkillCard":
        return cw.POCKET_SKILL
    elif ctype == "ItemCard":
        return cw.POCKET_ITEM
    elif ctype == "BeastCard":
        return cw.POCKET_BEAST
    else:
        assert False


class CardHeader(object):
    name: str

    scenario: str
    author: str

    wsnversion: str
    scenariocard: bool
    scedir: str

    penalty: bool
    recycle: bool

    versionhint: Optional[Tuple[str, str, bool, bool, bool]]

    star: int
    deal_per: int
    wxrect: pygame.rect.Rect
    negaflag: bool
    clickedflag: bool
    textpos: Tuple[int, int]
    subrect: pygame.rect.Rect

    def __init__(self, data: Optional[cw.data.CWPyElement] = None, owner: Optional["cw.character.Character"] = None,
                 carddata: Optional[cw.data.CWPyElement] = None, from_scenario: bool = False, scedir: str = "",
                 put_db: bool = False, dbrec: Optional[sqlite3.Row] = None, imgdbrec: Optional[sqlite3.Cursor] = None,
                 dbowner: str = "STOREHOUSE", bgtype: str = "") -> None:
        self.ref_original = weakref.ref(self)
        self.order = -1
        if dbrec:
            self.set_owner(dbowner)
            self.carddata = None
            self.fpath = dbrec["fpath"]
            self.type: str = dbrec["type"]
            self.id = dbrec["id"]
            self.name = dbrec["name"]
            self.imgpaths = to_imgpaths(dbrec, imgdbrec)
            self.desc = dbrec["desc"]
            self.scenario = dbrec["scenario"]
            self.author = dbrec["author"]
            self.keycodes: List[str] = dbrec["keycodes"].split("\n")
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
            self.flags = {}
            self.steps = {}
            self.variants = {}
            if dbowner == "BACKPACK":
                from_scenario = bool(dbrec["scenariocard"])
            self.versionhint = cw.cwpy.sct.from_basehint(dbrec["versionhint"])
            wsnversion = dbrec["wsnversion"]  # ""の場合はWsn.1以前
            self.wsnversion = wsnversion if wsnversion is not None else ""
            self.moved = dbrec["moved"]
            self.star = dbrec["star"]
            self.need_resetvariables = bool(dbrec["resetvariables"])
        else:
            assert carddata is not None
            self.set_owner(owner)
            self.carddata = carddata
            self.wsnversion = carddata.getattr(".", "dataVersion", "")

            if data is not None:
                self.fpath = data.fpath
                self.type = os.path.basename(os.path.dirname(self.fpath))
            elif carddata is not None:
                self.fpath = ""
                self.type = carddata.tag
                data = carddata.find_exists("Property")
            assert data is not None

            self.id = data.getint("Id", 0)
            self.name = data.gettext("Name", "")
            self.desc = data.gettext("Description", "")
            self.scenario = data.gettext("Scenario", "")
            self.author = data.gettext("Author", "")
            keycodes = data.gettext("KeyCodes", "")
            self.keycodes = cw.util.decodetextlist(keycodes) if keycodes else []
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

            self.need_resetvariables = self.carddata.getbool(".", "resetvariables", False)
            self.flags = cw.data.init_flags(self.carddata, True)
            self.steps = cw.data.init_steps(self.carddata, True)
            self.variants = cw.data.init_variants(self.carddata, True)

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
        self._cardimg: Optional[cw.image.CardImage] = None
        self.rect = cw.s(pygame.rect.Rect(0, 0, 80, 110))
        self.wxrect = cw.wins(pygame.rect.Rect(0, 0, 80, 110))
        # cardcontrolダイアログで使うフラグ
        self.negaflag = False
        self.clickedflag = False
        self.deal_per = 100
        # CharaInfoダイアログで使う表示位置情報
        self.textpos = (0, 0)
        self.subrect = pygame.rect.Rect(0, 0, 0, 0)

        # 特殊なキーコード
        self.penalty = bool(cw.cwpy.msgs["penalty_keycode"] in self.keycodes)
        if not scenariocard and self.type == "BeastCard" and\
                isinstance(owner, (cw.character.Friend, cw.character.Enemy)):
            # 最初から持っていた使用回数ありリサイクル召喚獣に限っては
            # 付帯能力でなくてもリサイクル状態が有効になる
            reattachment = True
        else:
            reattachment = (self.attachment or self.type == "ItemCard")
        self.recycle = bool(self.type in ("ItemCard", "BeastCard") and
                            cw.cwpy.msgs["recycle_keycode"] in self.keycodes and reattachment)
        self.keycodes.append(self.name)

        # 所持スキルカードだった場合は使用回数を設定
        if self.is_ccardheader() and self.type == "SkillCard":
            self.get_uselimit()

        # 荷物袋にある時の私有者
        self.personal_owner: Optional[cw.sprite.card.PlayerCard] = None
        self.personal_owner_index = (-1, -1)

        # ソート用の型ID
        if self.type == "SkillCard":
            self.type_id = 0
        elif self.type == "ItemCard":
            self.type_id = 1
        else:
            self.type_id = 2

        # ソート用の適性値
        self.vocation_for_sort = 0

        # 遅延書き込み
        self._lazy_write: Optional[cw.data.CWPyElementTree] = None

    @property
    def negastar(self) -> int:
        if self.star is None:
            return 0
        return -self.star

    def get_showingname(self) -> str:
        return self.name

    def set_cardimg(self, imgpaths: List["cw.image.ImageInfo"], can_loaded_scaledimage: bool,
                    anotherscenariocard: bool) -> None:
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
                                           can_loaded_scaledimage=can_loaded_scaledimage,
                                           is_scenariocard=self.scenariocard,
                                           anotherscenariocard=anotherscenariocard, scedir=self.scedir)
        self.rect = pygame.rect.Rect(self.rect)
        self.rect.size = self._cardimg.rect.size
        self.wxrect = pygame.rect.Rect(self._cardimg.wxrect)
        self._cardscale = cw.UP_SCR
        self._wxcardscale = cw.UP_WIN
        self._skindirname = cw.cwpy.setting.skindirname
        self._bordering_cardname = cw.cwpy.setting.bordering_cardname
        self._show_premiumicon = cw.cwpy.setting.show_premiumicon

    def update_scenariopath(self, normpath: str, dst: str) -> None:
        if not self.scenariocard:
            return
        normpath2 = cw.util.get_keypath(self.scedir)
        if normpath != normpath2:
            return
        self._cardimg = None
        self.scedir = dst

    def get_owner(self) -> Optional[Union[List["CardHeader"], "cw.character.Character"]]:
        if self._owner == "BACKPACK":
            assert cw.cwpy.ydata
            assert cw.cwpy.ydata.party
            return cw.cwpy.ydata.party.backpack
        elif self._owner == "STOREHOUSE":
            assert cw.cwpy.ydata
            return cw.cwpy.ydata.storehouse
        elif self._owner:
            assert isinstance(self._owner, weakref.ReferenceType)
            return self._owner()
        else:
            return None

    def set_owner(self, owner: Optional[Union["cw.character.Character", str]]) -> None:
        if isinstance(owner, cw.character.Character):
            self._owner: Optional[Union[str, weakref.ReferenceType[cw.character.Character]]] = weakref.ref(owner)
        else:
            self._owner = owner

    def get_bgtype(self) -> str:
        if self.bgtype:
            return self.bgtype
        if self.type == "BeastCard" and self.attachment:
            return "OPTION"
        return self.type.upper().replace("CARD", "")

    @property
    def cardimg(self) -> "cw.image.CardImage":
        if not self._cardimg or self._cardscale != cw.UP_SCR or\
                self._wxcardscale != cw.UP_WIN or\
                self._skindirname != cw.cwpy.setting.skindirname or\
                self._bordering_cardname != cw.cwpy.setting.bordering_cardname or\
                self._show_premiumicon != cw.cwpy.setting.show_premiumicon:
            if self.carddata is None:
                rootattrs = GetRootAttribute(self.fpath)
                can_loaded_scaledimage = cw.util.str2bool(rootattrs.attrs.get("scaledimage", "False"))
                anotherscenariocard = cw.util.str2bool(rootattrs.attrs.get("anotherscenariocard", "False"))
            else:
                can_loaded_scaledimage = self.carddata.getbool(".", "scaledimage", False)
                anotherscenariocard = self.carddata.getbool(".", "anotherscenariocard", False)
            self.set_cardimg(self.imgpaths, can_loaded_scaledimage, anotherscenariocard)
            assert self._cardimg is not None
        return self._cardimg

    def get_cardwxbmp(self, test_aptitude: Optional["cw.sprite.card.PlayerCard"] = None) -> wx.Bitmap:
        return self.cardimg.get_cardwxbmp(self, test_aptitude=test_aptitude)

    def get_cardimg(self) -> pygame.surface.Surface:
        return self.cardimg.get_cardimg(self)

    def set_resetvariables(self, resetvariables: bool) -> None:
        assert self.carddata is not None
        self.need_resetvariables = resetvariables
        if self.carddata is not None:
            if resetvariables:
                self.carddata.set("resetvariables", str(resetvariables))
            elif "resetvariables" in self.carddata.attrib:
                self.carddata.attrib.pop("resetvariables")
        owner = self.get_owner()
        if owner and isinstance(owner, cw.character.Character) and owner.data is not None:
            owner.data.is_edited = True

    def do_write(self, dupcheck: bool = True) -> None:
        if self._lazy_write is not None:
            assert cw.cwpy.ydata
            if dupcheck:
                self._lazy_write.fpath = cw.util.dupcheck_plus(self._lazy_write.fpath)
            self._lazy_write.write_xml(True)
            self.fpath = self._lazy_write.fpath
            self._lazy_write = None

            # self.fpathを削除予定のfpathリストから削除
            cw.cwpy.ydata.deletedpaths.discard(self.fpath)

    def get_vocation_level(self, owner: "cw.character.Character", enhance_act: bool = False) -> int:
        """
        適性値の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
        enhance_act : 行動力を加味する場合、True
        """
        return cw.effectmotion.get_vocation_level(owner, self.vocation, enhance_act=enhance_act)

    def get_showed_vocation_level(self, owner: "cw.character.Character") -> int:
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

    def get_vocation_val(self, owner: "cw.character.Character", enhance_act: bool = False) -> int:
        """
        適性値(身体特性+精神特性の合計値)を返す。
        enhance_act : 行動力を加味する場合、True
        """
        if not owner:
            owner_c = self.get_owner()
            assert isinstance(owner_c, cw.character.Character)
            owner = owner_c
        return cw.effectmotion.get_vocation_val(owner, self.vocation, enhance_act=enhance_act)

    def set_testaptitude(self, test_aptitude: Optional["cw.character.Character"]) -> None:
        """ソート用の適性値を計算する。
        Noneを指定する事でリセットする。
        """
        if test_aptitude:
            self.vocation_for_sort = -self.get_showed_vocation_level(owner=test_aptitude)
        else:
            self.vocation_for_sort = 0

    def get_uselimit_level(self) -> int:
        """
        使用回数の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
        """
        limit, maxlimit = self.get_uselimit()
        if maxlimit <= 0:
            return 0
        limitper = 100 * limit // maxlimit

        if maxlimit <= limit:
            value = 4
        elif limit == 1:  # MAX状態以外で残り1回なら
            value = 1
        elif limitper > 50:
            value = 3
        elif 50 >= limitper > 0:
            value = 2
        elif limitper == 0:
            value = 0
        else:
            assert False

        return value

    def get_uselimit(self, reset: bool = False) -> Tuple[int, int]:
        """
        (使用回数, 最大使用回数)を返す。
        """
        if self.is_ccardheader() and self.type == "SkillCard" and (not self.maxuselimit or reset):
            owner = self.get_owner()
            assert isinstance(owner, cw.character.Character)
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
                    not isinstance(self.get_owner(), cw.character.Player) or\
                    self.uselimit > self.maxuselimit:
                self.uselimit = self.maxuselimit

        return self.uselimit, self.maxuselimit

    def get_enhance_val_used(self) -> Tuple[int, int, int]:
        """
        カード使用時に設定されている強化値を、
        (回避値, 抵抗値, 防御値)の順のタプルで返す。
        """
        if self.type in ("ActionCard", "SkillCard", "ItemCard"):
            return self.enhance_avo_used, self.enhance_res_used, self.enhance_def_used
        else:
            return 0, 0, 0

    def get_enhance_val(self) -> Tuple[int, int, int]:
        """
        カード所持時に設定されている強化値を、
        (回避値, 抵抗値, 防御値)の順のタプルで返す。
        """
        if self.type in ("ItemCard", "BeastCard"):
            return self.enhance_avo, self.enhance_res, self.enhance_def
        else:
            return 0, 0, 0

    def set_uselimit(self, value: int, animate: bool = False) -> None:
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
            assert header.carddata is not None
            header.uselimit += value
            header.uselimit = cw.util.numwrap(header.uselimit, 0, header.maxuselimit)
            e = header.carddata.find_exists("Property/UseLimit")
            e.text = str(header.uselimit)
            if owner:
                assert isinstance(owner, cw.character.Character)
                owner.data.is_edited = True
                if owner.deck:
                    owner.deck.update_skillcardimage(header)
        # アイテムカード。
        elif header.type == "ItemCard" and not header.maxuselimit == 0:
            assert header.carddata is not None
            header.uselimit += value
            header.uselimit = cw.util.numwrap(header.uselimit, 0, 999)
            e = header.carddata.find_exists("Property/UseLimit")
            e.text = str(header.uselimit)
            if owner:
                assert isinstance(owner, cw.character.Character)
                owner.data.is_edited = True

                # カード消滅処理。リサイクルカードの場合は消滅させない
                if header.uselimit <= 0 and not header.recycle and header.get_owner() == owner:
                    if cw.cwpy.battle and header in owner.deck.hand:
                        owner.deck.hand.remove(header)

                    cw.cwpy.trade("TRASHBOX", header=header, from_event=True, clearinusecard=False)

        # 召喚獣カード。
        elif header.type == "BeastCard" and not header.maxuselimit == 0:
            assert header.carddata is not None
            header.uselimit += value
            header.uselimit = cw.util.numwrap(header.uselimit, 0, 999)
            e = header.carddata.find_exists("Property/UseLimit")
            e.text = str(header.uselimit)
            if owner:
                assert isinstance(owner, (cw.sprite.card.PlayerCard,
                                          cw.sprite.card.EnemyCard,
                                          cw.sprite.card.FriendCard))
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

    def write(self, party: Optional[cw.data.Party] = None, move: bool = False, from_getcontent: bool = False) -> None:
        def create_newpath(party: Optional[cw.data.Party]) -> str:
            fname = cw.util.repl_dischar(self.name) + ".xml"
            if self._owner == "BACKPACK":
                if not party:
                    assert cw.cwpy.ydata
                    assert cw.cwpy.ydata.party
                    party = cw.cwpy.ydata.party
                dpath = os.path.dirname(party.path)
            else:
                dpath = cw.cwpy.yadodir
            path = cw.util.join_paths(dpath, self.type, fname)
            return cw.util.dupcheck_plus(path)

        if move:
            assert cw.cwpy.ydata
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

    def contain_xml(self, load: bool = True) -> None:
        if not load and self._lazy_write is not None:
            return
        if self.carddata is None:
            if load:
                self.do_write()
                e = cw.data.yadoxml2etree(self.fpath)
                self.carddata = e.getroot()
                self.flags = cw.data.init_flags(self.carddata, True)
                self.steps = cw.data.init_steps(self.carddata, True)
                self.variants = cw.data.init_variants(self.carddata, True)
            if self._lazy_write is None:
                # self.fpathを削除予定のfpathリストに追加
                assert cw.cwpy.ydata
                cw.cwpy.ydata.deletedpaths.add(self.fpath, self.scenariocard)

    def remove_importedmaterials(self) -> None:
        # 取り込み素材をフォルダごと削除
        if self.carddata is None:
            self.do_write()
            self.carddata = cw.data.yadoxml2element(self.fpath)
            self.flags = cw.data.init_flags(self.carddata, True)
            self.steps = cw.data.init_steps(self.carddata, True)
            self.variants = cw.data.init_variants(self.carddata, True)

        emp = self.carddata.find("Property/Materials")
        if emp is not None:
            assert cw.cwpy.ydata
            mates = cw.util.join_yadodir(emp.text)
            cw.cwpy.ydata.deletedpaths.add(mates, True)

    def set_scenariostart(self) -> None:
        """
        シナリオ開始時に呼ばれる。
        """
        if self.is_ccardheader() and self.type == "SkillCard":
            assert self.carddata is not None
            e = self.carddata.find_exists("Property/UseLimit")
            e.text = str(self.uselimit)
            owner = self.get_owner()
            assert isinstance(owner, cw.character.Character)
            owner.data.is_edited = True
        elif self.is_backpackheader() and self.scenariocard and self.carddata is not None:
            imgpaths = cw.image.get_imageinfos(self.carddata.find_exists("Property"))
            self.set_cardimg(imgpaths, can_loaded_scaledimage=self.carddata.getbool(".", "scaledimage", False),
                             anotherscenariocard=self.carddata.getbool(".", "anotherscenariocard", False))

    def set_scenarioend(self) -> None:
        """
        シナリオ終了時に呼ばれる。
        非付帯召喚カードを削除したり、
        シナリオで取得したカードの素材ファイルを宿にコピーしたりする。
        """
        assert cw.cwpy.ydata
        assert cw.cwpy.ydata.party
        self.do_write()
        if self.scenariocard:
            if self.carddata is None:
                assert self.is_backpackheader()
                if cw.fsync.is_waiting(self.fpath):
                    cw.fsync.sync()
                assert self.fpath, self.name
                assert os.path.isfile(self.fpath), self.fpath
                self.carddata = cw.data.xml2element(self.fpath)
                self.flags = cw.data.init_flags(self.carddata, True)
                self.steps = cw.data.init_steps(self.carddata, True)
                self.variants = cw.data.init_variants(self.carddata, True)

            # シナリオ取得フラグクリア
            self.scenariocard = False
            self.scedir = ""
            if "scenariocard" in self.carddata.attrib:
                self.carddata.attrib.pop("scenariocard")
            if "anotherscenariocard" in self.carddata.attrib:
                self.carddata.attrib.pop("anotherscenariocard")
            # 画像コピー
            dstdir = cw.util.join_paths(cw.cwpy.yadodir, "Material", self.type, self.name if self.name else "noname")
            dstdir = cw.util.dupcheck_plus(dstdir)
            can_loaded_scaledimage = self.carddata.getbool(".", "scaledimage", False)
            cw.cwpy.copy_materials(self.carddata, dstdir, can_loaded_scaledimage=can_loaded_scaledimage)
            # 画像更新
            self.imgpaths = cw.image.get_imageinfos(self.carddata.find_exists("Property"))
            self.set_cardimg(self.imgpaths, can_loaded_scaledimage=self.carddata.getbool(".", "scaledimage", False),
                             anotherscenariocard=False)
            if self.need_resetvariables:
                self.reset_variables()
            if self.is_backpackheader():
                self.write()
                self.carddata = None
                self.flags = {}
                self.steps = {}
                self.variants = {}

        elif self.type == "BeastCard" and not self.attachment:
            cw.cwpy.trade("TRASHBOX", header=self, from_event=True)

        elif self.need_resetvariables:
            if self.carddata is None:
                assert self.is_backpackheader()
                if cw.fsync.is_waiting(self.fpath):
                    cw.fsync.sync()
                assert self.fpath, self.name
                assert os.path.isfile(self.fpath), self.fpath
                self.carddata = cw.data.xml2element(self.fpath)
                self.flags = cw.data.init_flags(self.carddata, True)
                self.steps = cw.data.init_steps(self.carddata, True)
                self.variants = cw.data.init_variants(self.carddata, True)
            self.reset_variables()
            if self.is_backpackheader():
                self.write()
                self.carddata = None
                self.flags = {}
                self.steps = {}
                self.variants = {}

        if self.is_ccardheader() and self.type == "SkillCard" and self.carddata is not None:
            self.carddata.find_exists("Property/UseLimit").text = "0"

        if self.is_ccardheader():
            owner = self.get_owner()
            assert isinstance(owner, cw.character.Character)
            owner.data.is_edited = True
        elif self.is_backpackheader():
            cw.cwpy.ydata.party.data.is_edited = True

    def reset_variables(self) -> None:
        """シナリオ終了時の状態変数初期化処理を行う。"""
        assert self.carddata is not None
        if not self.need_resetvariables:
            return
        for e in self.carddata.getfind("Flags", False):
            if e.getattr(".", "initialize", "Leave") == "Leave":
                e.set("value", e.get("default"))
        for e in self.carddata.getfind("Steps", False):
            if e.getattr(".", "initialize", "Leave") == "Leave":
                e.set("value", e.get("default"))
        for e in self.carddata.getfind("Variants", False):
            if e.getattr(".", "initialize", "Leave") == "Leave":
                e.set("type", e.get("defaulttype"))
                e.set("value", e.get("defaultvalue"))

        for flag in self.flags.values():
            if flag.initialization == "Leave":
                flag.set(flag.defaultvalue)
        for step in self.steps.values():
            if step.initialization == "Leave":
                step.set(step.defaultvalue)
        for variant in self.variants.values():
            if variant.initialization == "Leave":
                variant.set(variant.defaultvalue)

        if "resetvariables" in self.carddata.attrib:
            self.carddata.attrib.pop("resetvariables")
        self.need_resetvariables = False
        if isinstance(self.carddata, cw.data.CWPyElementTree):
            self.carddata.is_edited = True

    def copy(self) -> "CardHeader":
        """
        Deckクラスで呼ばれる用。
        CardImageインスタンスを新しく生成して返す。
        """
        assert self.carddata is not None
        header = copy.copy(self)
        header.set_cardimg(self.imgpaths, can_loaded_scaledimage=self.carddata.getbool(".", "scaledimage", False),
                           anotherscenariocard=self.carddata.getbool(".", "anotherscenariocard", False))
        return header

    def is_ccardheader(self) -> bool:
        return bool(isinstance(self._owner, weakref.ref))

    def is_backpackheader(self) -> bool:
        return bool(self._owner == "BACKPACK")

    def is_storehouseheader(self) -> bool:
        return bool(self._owner == "STOREHOUSE")

    def is_hold(self) -> bool:
        if self.type == "SkillCard":
            pocket = cw.POCKET_SKILL
        elif self.type == "ItemCard":
            pocket = cw.POCKET_ITEM
        elif self.type == "BeastCard":
            pocket = cw.POCKET_BEAST
        else:
            pocket = -1

        if pocket != -1:
            owner = self.get_owner()
            if (self.hold or (isinstance(owner, cw.character.Character) and owner.hold_all[pocket])) and\
                    not self.penalty and self.type != "BeastCard":
                # ホールド(ペナルティカード以外)
                return True
        return False

    def is_autoselectable(self) -> bool:
        card = self.ref_original()
        assert card

        if card.recycle and card.uselimit <= 0:
            # 使用回数0(リサイクルカードのみ)
            return False

        if card.is_hold():
            # ホールド(ペナルティカード以外)
            return False

        # 対象無しまたは効果無し
        noeffect = bool(card.target == "None")
        if card.carddata is not None:
            noeffect |= card.carddata.find("Motions/Motion") is None

        owner = card.get_owner()
        silence = False
        if card.carddata is not None and owner:
            assert isinstance(owner, cw.character.Character)
            # 沈黙(行動不能も同様に扱う)
            spell = card.carddata.getbool("Property/EffectType", "spell", False)
            silence |= (owner.is_silence() or owner.is_inactive()) and spell

            if card.type != "BeastCard":
                # 魔法無効状態
                effecttype = card.carddata.gettext("Property/EffectType", "")
                magic = effecttype in ("Magic", "PhysicalMagic")
                silence |= owner.is_antimagic() and magic

        if not silence:
            # 使用時ボーナス・ペナルティがあるカードは効果がなくても選択可能
            # ただしCardWirthでは沈黙・魔法無効化の影響は受ける
            if card.enhance_avo_used != 0 or\
               card.enhance_res_used != 0 or\
               card.enhance_def_used != 0:
                return True

        return not (noeffect or silence)

    def get_targets(self) -> Tuple[List["cw.sprite.card.CWPyCard"], List["cw.sprite.card.CWPyCard"]]:
        """
        (ターゲットのリスト,
         効果のあるターゲットのリスト,
         優先すべきターゲットのリスト)
        を返す。
        """
        owner = self.get_owner()

        if self.target == "Both":
            if isinstance(owner, cw.character.Enemy):
                targets: List[cw.sprite.card.CWPyCard] = []
                targets.extend(cw.cwpy.get_ecards("unreversed"))
                targets.extend(cw.cwpy.get_pcards("unreversed"))
            else:
                targets = []
                targets.extend(cw.cwpy.get_pcards("unreversed"))
                targets.extend(cw.cwpy.get_ecards("unreversed"))
        elif self.target == "Party":
            if isinstance(owner, cw.character.Enemy):
                targets = []
                targets.extend(cw.cwpy.get_ecards("unreversed"))
            else:
                targets = []
                targets.extend(cw.cwpy.get_pcards("unreversed"))

        elif self.target == "Enemy":
            if isinstance(owner, cw.character.Enemy):
                targets = []
                targets.extend(cw.cwpy.get_pcards("unreversed"))
            else:
                targets = []
                targets.extend(cw.cwpy.get_ecards("unreversed"))

        elif self.target == "User":
            assert isinstance(owner, cw.sprite.card.CWPyCard)
            targets = [owner]
        elif self.target == "None":
            targets = []

        effective = cw.effectmotion.get_effectivetargets(self, targets)
        return targets, effective

    def is_noeffect(self, target: "cw.character.Character") -> bool:
        assert self.carddata is not None
        effecttype = self.carddata.gettext("Property/EffectType", "")
        if cw.effectmotion.check_noeffect(effecttype, target):
            return True
        for e in self.carddata.getfind("Motions"):
            element = e.getattr(".", "element", "")
            if not cw.effectmotion.is_noeffect(element, target):
                return False
        return True

    def get_keycodes(self, with_name: bool = True) -> List[str]:
        if not with_name:
            return self.keycodes[:-1]

        # 互換動作: 1.20以前にカード名キーコードは存在しない
        if cw.cwpy.sdata and cw.cwpy.sct.lessthan("1.20", cw.cwpy.sdata.get_versionhint(frompos=cw.HINT_AREA)):
            return self.keycodes[:-1]
        else:
            return self.keycodes

    def find_keycode_position(self, matcher: Callable[[str], bool], startindex: int) -> int:
        """
        matcher(name)がTrueになるキーコードを
        startindexの位置から検索し、見つかった位置を返す。
        """
        keycodes = self.get_keycodes()
        if keycodes is not None:
            for i, keycode in enumerate(keycodes[startindex:]):
                if matcher(keycode):
                    return i + startindex
        return -1

    def get_keycode_at(self, index: int) -> str:
        """指定位置のキーコードを返す。添字が範囲外なら空文字を返す。"""
        keycodes = self.get_keycodes()
        if index >= 0 and index < len(keycodes):
            return keycodes[index]
        return ""

    def set_hold(self, hold: bool) -> None:
        assert cw.cwpy.ydata
        if self.type == "BeastCard":
            return

        cw.cwpy.ydata.changed()
        self.hold = hold
        owner = self.get_owner()
        if isinstance(owner, cw.character.Player):
            etree = cw.data.CWPyElementTree(element=self.carddata)
            etree.edit("Property/Hold", str(self.hold))
            owner.data.is_edited = True

    def set_star(self, star: int) -> None:
        assert cw.cwpy.ydata
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
                e_prop = data.find_exists("Property")
                e_prop.append(cw.data.make_element("Star", str(self.star)))
                data.is_edited = True
            else:
                data.edit("Property/Star", str(self.star))
            owner.data.is_edited = True
        else:
            data = cw.data.CWPyElementTree(self.fpath)
            e = data.find("Property/Star")
            if e is None:
                e_prop = data.find_exists("Property")
                e_prop.append(cw.data.make_element("Star", str(self.star)))
                data.is_edited = True
            else:
                data.edit("Property/Star", str(self.star))
            data.write_xml()
            self.fpath = data.fpath

    @property
    def sellingprice(self) -> int:
        """カードの売却価格。"""
        # 互換動作: 1.30以前ではカードの売値は常に半額
        if cw.cwpy.sct.lessthan("1.30", self.versionhint):
            price: int = self.price // 2
        elif self.premium == "Normal":
            price = self.price // 2
        else:
            price = int(self.price * 0.75)

        if self.type == "ItemCard" and 0 < self.maxuselimit:
            # 使用回数がある場合は使うほど売値が減る
            price = price * self.uselimit // self.maxuselimit

        return price

    def can_selling(self) -> bool:
        """売却可能か？"""
        # プレミアカードは売却・破棄できない(イベントからの呼出以外)
        if not cw.cwpy.is_debugmode() and cw.cwpy.setting.protect_premiercard and\
                self.premium == "Premium":
            return False

        # スターつきのカードは売却・破棄できない(イベントからの呼出以外)
        if cw.cwpy.setting.protect_staredcard and self.star:
            return False

        return True

    def is_removewithstatus(self, ccard: Union["cw.character.Character", "cw.sprite.card.MenuCard"]) -> bool:
        """召喚獣カードが消滅する状態か？"""
        assert self.carddata is not None
        return is_removewithstatus(self.carddata, ccard)

    def is_activewithstatus(self, ccard: "cw.character.Character") -> bool:
        """ccardはこの召喚獣カードが発動可能な状態か？"""
        if self.carddata is None:
            prop = cw.data.xml2element(self.fpath, "Property")
            e = prop.find("InvocationCondition")
        else:
            e = self.carddata.find("Property/InvocationCondition")
        if e is None:
            return ccard.is_alive()
        for e_status in e:
            if e_status.tag == "Status" and e_status.text:
                methodname = "is_" + e_status.text.lower()
                if hasattr(ccard, methodname) and getattr(ccard, methodname)():
                    return True
        return False

    def get_showstyle(self) -> str:
        """発動時の視覚効果(Wsn.4)。"""
        if self.carddata is None:
            prop = cw.data.xml2element(self.fpath, "Property")
            e = prop.find("ShowStyle")
        else:
            e = self.carddata.find("Property/ShowStyle")
        if e is None:
            if self.type == "BeastCard":
                return "Center"
            else:
                return "FrontOfUser"
        return e.text

    def get_can_loaded_scaledimage(self) -> bool:
        """スケーリングされたイメージを使用可能なカードか。"""
        if self.carddata is None:
            self.do_write()
            rootattrs = GetRootAttribute(self.fpath)
            return cw.util.str2bool(rootattrs.attrs.get("scaledimage", "False"))
        else:
            result: bool = self.carddata.getbool(".", "scaledimage", False)
            return result


def is_removewithstatus(carddata: cw.data.CWPyElement,
                        target: Union["cw.character.Character", "cw.sprite.card.MenuCard"]) -> bool:
    """targetはcarddataの召喚獣カードが消滅する状態か？"""
    if not isinstance(target, cw.character.Character):
        return False
    e = carddata.find("Property/RemovalCondition")
    if e is None:
        # 消滅条件が設定されていない場合は意識不明の時に消滅
        return target.is_unconscious()
    for e2 in e:
        if e2.tag == "Status" and e2.text:
            if e2.text != "Unconscious":
                # Wsn.3以前では仕様上意識不明以外の消滅条件は指定不可であるため
                # ここで弾いておく
                continue
            methodname = "is_" + e2.text.lower()
            if hasattr(target, methodname) and getattr(target, methodname)():
                # 消滅条件に引っかかる(Wsn.3)
                return True
    return False


class InfoCardHeader(object):
    scenario: str
    author: str

    deal_per: int
    wxrect: pygame.rect.Rect
    negaflag: bool
    clickedflag: bool

    def __init__(self, data: cw.data.CWPyElement, can_loaded_scaledimage: bool) -> None:
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
        self.deal_per = 100

    def set_cardimg(self, can_loaded_scaledimage: bool, anotherscenariocard: bool) -> None:
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
    def cardimg(self) -> "cw.image.CardImage":
        if self._cardscale != cw.UP_SCR or\
                self._wxcardscale != cw.UP_WIN or\
                self._skindirname != cw.cwpy.setting.skindirname or\
                self._bordering_cardname != cw.cwpy.setting.bordering_cardname:
            self.set_cardimg(self.can_loaded_scaledimage, False)
        return self._cardimg

    def get_cardwxbmp(self, test_aptitude: Optional["cw.sprite.card.PlayerCard"] = None) -> wx.Bitmap:
        if self.negaflag:
            return self.cardimg.get_wxnegabmp()
        else:
            return self.cardimg.get_wxbmp()

    def get_cardimg(self) -> pygame.surface.Surface:
        if self.negaflag:
            return self.cardimg.get_negaimg()
        else:
            return self.cardimg.get_image()


class AdventurerHeader(object):
    def __init__(self, data: Optional[cw.data.CWPyElement] = None, album: bool = False,
                 dbrec: Optional[sqlite3.Row] = None, imgdbrec: Optional[sqlite3.Cursor] = None,
                 fpath: str = "", rootattrs: Optional[Dict[str, str]] = None) -> None:
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
            r_gene = re.compile("＠Ｇ\\d{10}$")

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
                elif name == "＠ＥＰ":
                    self.ep = int(attrs.get("value", 0))
                elif name == "＿消滅予約":
                    self.leavenoalbum = True
                elif r_gene.match(name):
                    self.gene.set_str(name[2:], int(attrs.get("value", 0)))
                elif name.startswith("＠Ｒ"):
                    self.race = name[2:]

                self.history.append(name)

        else:
            assert data is not None
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
            r_gene = re.compile("＠Ｇ\\d{10}$")
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

            for e in reversed(data.getfind("Coupons")):
                if not e.text:
                    continue
                elif e.text in ages:
                    self.age = e.text
                elif e.text in sexs:
                    self.sex = e.text
                elif e.text == "＠ＥＰ":
                    self.ep = e.getint(".", "value", 0)
                elif e.text == "＿消滅予約":
                    self.leavenoalbum = True
                elif r_gene.match(e.text):
                    self.gene.set_str(e.text[2:], e.getint(".", "value", 0))
                elif e.text.startswith("＠Ｒ"):
                    self.race = e.text[2:]

                self.history.append(e.text)

    def made_baby(self) -> None:
        """
        EP減少と子作り回数加算を行ったXMLファイルを書き出す。
        """
        n = 0
        for period in cw.cwpy.setting.periods:
            if self.age == "＿" + period.name:
                if self.album:
                    n = period.spendep // 2
                else:
                    n = period.spendep
                break
        if n == 0:
            return

        self.ep -= n
        data = cw.data.yadoxml2etree(self.fpath)
        r_gene = re.compile("＠Ｇ\\d{10}$")

        ep = False
        gene = False
        for e in data.getfind("Property/Coupons"):
            if ep and gene:
                break
            if not e.text:
                continue

            # EP減少
            if e.text == "＠ＥＰ" and not ep:
                e.attrib["value"] = str(e.getint(".", "value") - n)
                ep = True
            # 子作り回数加算
            elif r_gene.match(e.text) and not gene:
                self.gene.count = e.getint(".", "value") + 1
                e.attrib["value"] = str(self.gene.count)
                gene = True

        data.write_xml(True)

    def grow(self) -> None:
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

        nextage = cw.cwpy.setting.periodcoupons[index + 1]
        data = cw.data.yadoxml2etree(self.fpath)
        advdata = cw.dialog.create.AdventurerData()

        # 能力値を再調整。ただし精神傾向は変化しない
        p = data.find_exists("Property/Ability/Physical")
        m = data.find_exists("Property/Ability/Mental")
        advdata.dex = p.getint(".", "dex", 0)
        advdata.agl = p.getint(".", "agl", 0)
        advdata.int = p.getint(".", "int", 0)
        advdata.str = p.getint(".", "str", 0)
        advdata.vit = p.getint(".", "vit", 0)
        advdata.min = p.getint(".", "min", 0)
        advdata.aggressive = m.getfloat(".", "aggressive", 0.0)
        advdata.cheerful = m.getfloat(".", "cheerful", 0.0)
        advdata.brave = m.getfloat(".", "brave", 0.0)
        advdata.cautious = m.getfloat(".", "cautious", 0.0)
        advdata.trickish = m.getfloat(".", "trickish", 0.0)
        race = self.get_race()
        advdata.maxdex = race.dex + 6
        advdata.maxagl = race.agl + 6
        advdata.maxint = race.int + 6
        advdata.maxstr = race.str + 6
        advdata.maxvit = race.vit + 6
        advdata.maxmin = race.min + 6

        cw.cwpy.setting.periods[index].demodulate(advdata, mental=False)
        cw.cwpy.setting.periods[index + 1].modulate(advdata, mental=False)
        cw.features.wrap_ability(advdata)

        p.set("dex", str(int(advdata.dex)))
        p.set("agl", str(int(advdata.agl)))
        p.set("int", str(int(advdata.int)))
        p.set("str", str(int(advdata.str)))
        p.set("vit", str(int(advdata.vit)))
        p.set("min", str(int(advdata.min)))

        for e in data.getfind("Property/Coupons"):
            if e.text != self.age:
                continue
            # 年代クーポンを上書き
            e.text = nextage
        self.age = nextage

        data.write_xml(True)

    def get_imgpaths(self) -> List["cw.image.ImageInfo"]:
        seq = []
        for info in self.imgpaths:
            seq.append(cw.image.ImageInfo(cw.util.join_yadodir(info.path), base=info))
        return seq

    def get_age(self) -> str:
        for period in cw.cwpy.setting.periods:
            if self.age == "＿" + period.name:
                return period.subname
        return ""

    def get_sex(self) -> str:
        for sex in cw.cwpy.setting.sexes:
            if self.sex == "＿" + sex.name:
                return sex.subname
        return ""

    def get_race(self) -> "RaceHeader":
        if self.race:
            for race in cw.cwpy.setting.races:
                if race.name == self.race:
                    return race
        return cw.cwpy.setting.unknown_race


class Gene(object):
    def __init__(self, bits: Optional[List[int]] = None, count: int = 0) -> None:
        if bits:
            self.bits = bits
        else:
            self.bits = [0 for _cnt in range(10)]

        self.count = count

    def get_str(self) -> str:
        return "".join([str(bit) for bit in self.bits])

    def set_str(self, s: str, count: int = 0) -> None:
        self.bits = [int(char) for char in s]
        self.count = count

    def reverse_bit(self, index: int) -> None:
        if 0 <= index < 10:
            self.bits[index] = 0 if self.bits[index] else 1

    def set_bit(self, index: int, value: int) -> None:
        if 0 <= index < 10:
            self.bits[index] = 1 if value else 0

    def set_randombit(self) -> None:
        n = cw.cwpy.dice.roll(sided=10)
        self.bits[n - 1] = 1

    def set_talentbit(self, talent: str, oldtalent: str = "") -> None:
        for nature in cw.cwpy.setting.natures:
            if "＿" + nature.name == talent:
                # 型に対応する型のbitを1にする
                for index in range(len(nature.genepattern)):
                    if nature.genepattern[index] == '1':
                        self.set_bit(index, 1)
                if nature.genecount == 0:
                    # 最弱遺伝子型(凡庸)
                    # 選択した型のbitも1にする
                    self.set_talentbit(oldtalent)
                break

    def count_bits(self) -> int:
        return len([bit for bit in self.bits if bit])

    def reverse(self) -> "Gene":
        bits = [int(not bit) for bit in self.bits]
        return Gene(bits)

    def fusion(self, gene: "Gene") -> "Gene":
        # 排他的論理和演算
        bits = [bit1 ^ bit2 for bit1, bit2 in zip(self.bits, gene.bits)]
        return Gene(bits)

    def rotate_father(self) -> "Gene":
        # 父親の遺伝情報のローテート(左へ)
        count = (self.count-1) % 10
        bits = self.bits[count:]
        bits.extend(self.bits[:count])
        return Gene(bits)

    def rotate_mother(self) -> "Gene":
        # 母親の遺伝情報のローテート(右へ)
        count = (10 - (self.count-1) % 10) % 10
        bits = self.bits[count:]
        bits.extend(self.bits[:count])
        return Gene(bits)


assert Gene([0, 1, 1, 0, 1, 0, 1, 0, 1, 1], 4).rotate_father().get_str() == "0101011011"
assert Gene([0, 1, 1, 0, 0, 0, 0, 0, 0, 1], 3).rotate_mother().get_str() == "0101100000"


class ScenarioHeader(object):
    def __init__(self, dbrec: Union[sqlite3.Row, Dict[str, Union[Optional[str], int, float, bool, Optional[bytes]]]],
                 imgdbrec: Union[Optional[sqlite3.Cursor], List[Dict[str, Union[int, str, Optional[bytes]]]]]) -> None:
        self.dpath = enforce_str(dbrec["dpath"])
        self.type = enforce_int(dbrec["type"])
        self.fname = enforce_str(dbrec["fname"])
        self.name = enforce_str(dbrec["name"])
        self.author = enforce_str(dbrec["author"])
        self.desc = enforce_str(dbrec["desc"])
        self.skintype = enforce_str(dbrec["skintype"])
        self.levelmin = enforce_int(dbrec["levelmin"])
        self.levelmax = enforce_int(dbrec["levelmax"])
        self.coupons = enforce_str(dbrec["coupons"])
        self.couponsnum = enforce_int(dbrec["couponsnum"])
        self.startid = enforce_int(dbrec["startid"])
        self.tags = enforce_str(dbrec["tags"])
        self.ctime = enforce_float_or_int(dbrec["ctime"])
        self.mtime = enforce_float_or_int(dbrec["mtime"])
        # ""の場合はWsn.1以前
        wsnversion = dbrec["wsnversion"]
        self.wsnversion = enforce_str(wsnversion) if wsnversion is not None else ""
        self.images: Dict[int, List[Optional[bytes]]] = {1: []}
        self.imgpaths = []

        image = enforce_optional_bytes(dbrec["image"])
        imgpath = enforce_optional_str(dbrec["imgpath"])
        if image or imgpath:
            self.images[1] = [image]
            self.imgpaths.append(cw.image.ImageInfo(path=imgpath if imgpath else ""))
        if imgdbrec:
            # 最大のindex
            maxorder = 0
            recs = []
            for imgrec in imgdbrec:
                scale = enforce_int(imgrec["scale"])
                imgpath = enforce_optional_str(imgrec["imgpath"])
                image = enforce_optional_bytes(imgrec["image"])
                postype = enforce_optional_str(imgrec["postype"])
                order = enforce_int(imgrec["numorder"])
                maxorder = max(maxorder, order)
                recs.append((scale, imgpath, image, postype, order))

            for scale, imgpath, image, postype, order in recs:
                if scale in self.images:
                    seq = self.images[scale]
                    if not seq:
                        seq.extend([None] * (maxorder+1))
                else:
                    seq = [None] * (maxorder+1)
                    self.images[scale] = seq
                seq[order] = image
                if not postype:
                    postype = "Default"
                if not imgpath:
                    imgpath = ""
                self.imgpaths.append(cw.image.ImageInfo(path=imgpath, postype=postype))

        self._wxbmps: Optional[List[wx.Bitmap]] = None
        self._wxbmps_noscale: Optional[List[wx.Bitmap]] = None
        self._imginfos: Optional[List[cw.image.ImageInfo]] = None
        self.skindir: Optional[str] = None
        self._up_win: Optional[float] = None
        self._up_scr: Optional[float] = None

    @property
    def mtime_reversed(self) -> Union[int, float]:
        """整列用の逆転した変更日時。"""
        return -self.mtime

    def get_fpath(self) -> str:
        return "/".join([self.dpath, self.fname])

    def set_fpath(self, fpath: str) -> None:
        self.dpath = os.path.dirname(fpath)
        self.fname = os.path.basename(fpath)

    def get_wxbmps(self, mask: bool = True) -> Tuple[List[wx.Bitmap], List[wx.Bitmap], List["cw.image.ImageInfo"]]:
        """スケールありの見出しイメージ(wx.Bitmap)、スケールなしの見出しイメージ、
        スケール情報を返す。"""
        if self._wxbmps is None or self.skindir != cw.cwpy.skindir or\
                self._up_win != cw.UP_WIN or self._up_scr != cw.UP_SCR:
            self.skindir = cw.cwpy.skindir
            self._up_win = cw.UP_WIN
            self._up_scr = cw.UP_SCR
            self._wxbmps = []
            self._wxbmps_noscale = []
            self._imginfos = []

            imagesx1 = self.images[1]
            scale_s = int(math.pow(2, int(math.log(cw.UP_SCR, 2))))

            for i, (imagex1, info) in enumerate(zip(imagesx1, self.imgpaths)):
                scale = scale_s
                while 1 <= scale:
                    if scale in self.images:
                        image = self.images[scale][i]
                        break
                    scale //= 2
                if image:
                    if imagex1 is None:
                        bmp_noscale = cw.util.empty_bitmap(1, 1)
                    else:
                        with io.BytesIO(imagex1) as f:
                            bmp_noscale = cw.util.load_wxbmp(f=f, mask=mask)
                            bmp_noscale.scr_scale = 1
                            f.close()
                    if scale == 1:
                        bmp = cw.wins(bmp_noscale)
                    else:
                        with io.BytesIO(image) as f:
                            bmp = cw.util.load_wxbmp(f=f, mask=mask)
                            bmp.scr_scale = scale
                            f.close()
                        bmp = cw.wins(bmp)
                    self._wxbmps_noscale.append(bmp_noscale)
                    self._wxbmps.append(bmp)
                    self._imginfos.append(info)
                elif info.path:
                    # スキンのTableフォルダを指定している場合はDBにバイナリが無い
                    path = cw.util.get_materialpathfromskin(info.path, cw.M_IMG)
                    if path:
                        bmp = cw.util.load_wxbmp(path, mask=mask, noscale=True)
                        self._wxbmps_noscale.append(bmp)
                        if not cw.UP_SCR == 1.0:
                            bmp = cw.util.load_wxbmp(path, mask=mask, can_loaded_scaledimage=True)
                        self._wxbmps.append(cw.wins(bmp))
                        self._imginfos.append(info)

        assert self._wxbmps_noscale is not None
        assert self._imginfos is not None
        return self._wxbmps, self._wxbmps_noscale, self._imginfos

    def get_bmps(self, mask: bool = True,
                 up_scr: Optional[float] = None) -> Optional[Tuple[List[pygame.surface.Surface],
                                                                   List["cw.image.ImageInfo"]]]:
        """
        スケールありの見出しイメージ(pygame.surface.Surface)、スケール情報を返す。
        指定スケールのイメージが存在しない場合はNoneを返す。
        """
        if up_scr is None:
            up_scr = cw.UP_SCR
        bmps = []
        imginfos = []

        # 指定スケールのイメージが存在するか確認する
        if up_scr == 1.0:
            has_scaledimage = True
        else:
            for info in self.imgpaths:
                if up_scr in self.images:
                    has_scaledimage = True
                    break
                if info.path:
                    path = cw.util.get_materialpathfromskin(info.path, cw.M_IMG)
                    if path:
                        spext = cw.util.splitext(path)
                        fname = "%s.x%s%s" % (spext[0], up_scr, spext[1])
                        if os.path.isfile(fname):
                            has_scaledimage = True
                            break
            else:
                has_scaledimage = False

        if not has_scaledimage:
            return None

        imagesx1 = self.images[1]
        scale_s = int(math.pow(2.0, int(math.log(up_scr, 2.0))))

        for i, (imagex1, info) in enumerate(zip(imagesx1, self.imgpaths)):
            scale = scale_s
            while 1 <= scale:
                if scale in self.images:
                    image = self.images[scale][i]
                    break
                scale //= 2
            if image:
                bmp_noscale: pygame.surface.Surface
                if imagex1:
                    with io.BytesIO(imagex1) as f:
                        bmp_noscale = cw.util.Depth1Surface(cw.util.load_image("", f=f, mask=mask, noscale=True), 1)
                        f.close()
                else:
                    bmp_noscale = pygame.surface.Surface((1, 1)).convert()
                    bmp_noscale.set_colorkey(bmp_noscale.get_at((0, 0)))
                if scale == 1:
                    bmp = bmp_noscale
                else:
                    with io.BytesIO(image) as f:
                        bmp = cw.util.Depth1Surface(cw.util.load_image("", f=f, mask=mask, noscale=True), scale)
                        f.close()
                bmps.append(bmp)
                imginfos.append(info)
            elif info.path:
                # スキンのTableフォルダを指定している場合はDBにバイナリが無い
                path = cw.util.get_materialpathfromskin(info.path, cw.M_IMG)
                if path:
                    bmp = cw.util.load_image(path, mask=mask, can_loaded_scaledimage=True, up_scr=scale_s)
                    bmps.append(bmp)
                    imginfos.append(info)

        return bmps, imginfos


class PartyHeader(object):
    def __init__(self, data: Optional[cw.data.CWPyElement] = None,
                 dbrec: Optional[sqlite3.Row] = None) -> None:
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
            assert data is not None
            self.fpath = data.fpath
            self.name = data.gettext("Name")
            self.money = data.getint("Money", 0)
            self.members = [e.text for e in data.getfind("Members") if e.text]

        self.data: Optional[cw.data.Party] = None
        self._memberprops: Optional[List[GetProperty]] = None
        self._membernames: Optional[List[str]] = None
        self._memberdescs: Optional[List[str]] = None
        self._membercoupons: Optional[List[List[str]]] = None
        self._memberlevels: Optional[List[int]] = None

    def is_adventuring(self) -> bool:
        path = cw.util.splitext(self.fpath)[0] + ".wsl"
        return bool(cw.util.get_yadofilepath(path))

    def get_sceheader(self) -> Optional[ScenarioHeader]:
        """
        現在冒険中のシナリオのScenarioHeaderを返す。
        """
        cw.fsync.sync()
        path = cw.util.splitext(self.fpath)[0] + ".wsl"
        path = cw.util.get_yadofilepath(path)

        if path:
            e = cw.util.get_elementfromzip(path, "ScenarioLog.xml", "Property")
            path = e.gettext("WsnPath", "")
            db = cw.cwpy.frame.open_scenariodb()
            if not db:
                return None
            sceheader: Optional[cw.header.ScenarioHeader] = db.search_path(path)
            return sceheader
        else:
            return None

    def get_memberpaths(self, yadodir: Optional[str] = None) -> List[str]:
        cw.fsync.sync()
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

    def _get_properties(self) -> List["GetProperty"]:
        if self._memberprops is None:
            self._memberprops = []
            for fpath in self.get_memberpaths():
                self._memberprops.append(GetProperty(fpath))
        return self._memberprops

    def get_membernames(self) -> List[str]:
        if self._membernames is None:
            self._membernames = []
            for prop in self._get_properties():
                self._membernames.append(prop.properties.get("Name", ""))
        return self._membernames

    def get_memberdescs(self) -> List[str]:
        if self._memberdescs is None:
            self._memberdescs = []
            for prop in self._get_properties():
                self._memberdescs.append(prop.properties.get("Description", ""))
        return self._memberdescs

    def get_membercoupons(self) -> List[List[str]]:
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

    def get_memberlevels(self) -> List[int]:
        if self._memberlevels is None:
            self._memberlevels = []
            for prop in self._get_properties():
                self._memberlevels.append(int(prop.properties.get("Level", "1")))
        return self._memberlevels

    @property
    def average_level(self) -> float:
        levels = self.get_memberlevels()
        return float(sum(levels))/len(levels) if len(levels) else 1.0

    @property
    def highest_level(self) -> int:
        return max(self.get_memberlevels())


class PartyRecordHeader(object):
    def __init__(self, fpath: Optional[str] = None,
                 dbrec: Optional[sqlite3.Row] = None,
                 partyrecord: Optional[cw.thread.StoredParty] = None) -> None:
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
                self.membernames.extend([""] * (len(self.members)-len(self.membernames)))
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
                self.membernames.append(member.gettext("Property/Name", ""))
            self.backpack = [header.name for header in partyrecord.backpack]
        else:
            assert fpath is not None
            etree = cw.data.xml2etree(fpath)
            self.fpath = etree.fpath
            self.name = etree.gettext("Property/Name")
            self.money = etree.getint("Property/Money", 0)
            self.members = []
            self.membernames = []
            for e in etree.getfind("Property/Members"):
                self.members.append(e.text if e.text else "")
                self.membernames.append(e.getattr(".", "name", ""))
            self.backpack = [e.get("name", "") for e in etree.getfind("BackpackRecord")]

    def rename_member(self, fpath: str, name: str) -> None:
        """メンバの改名を通知する。"""
        s = os.path.basename(fpath)
        s = cw.util.splitext(s)[0]
        if s in self.members:
            index = self.members.index(s)
            self.membernames[index] = name
            data = cw.data.xml2etree(self.fpath)
            data.edit("Property/Members/Member[%s]" % (index+1), name, "name")
            data.write_xml()

    def vanish_member(self, fpath: str) -> None:
        """メンバの消滅を通知する。"""
        s = os.path.basename(fpath)
        s = cw.util.splitext(s)[0]
        if s in self.members:
            index = self.members.index(s)
            self.members[index] = ""
            data = cw.data.xml2etree(self.fpath)
            ename = "Property/Members/Member[%s]" % (index+1)
            data.edit(ename, "")

            # 互換性維持の処理
            # 過去のデータでname属性が無い場合がある
            name = data.getattr(ename, "name", "")
            if not name:
                name = GetName(fpath).name
                self.membernames[index] = name
                data.edit(ename, "", "name")

            data.write_xml()

    def get_memberpaths(self) -> List[str]:
        cw.fsync.sync()
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

    def get_membernames(self) -> List[str]:
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
                seq.append("<Vanished>")

        return seq


class SavedJPDCImageHeader(object):
    """保存済みJPDCイメージ。
    宿・シナリオごとにJPDCで生成されたファイルを保存する。
    """
    def __init__(self, fpath: Optional[str] = None,
                 dbrec: Optional[sqlite3.Row] = None) -> None:
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
            self.scenarioname = data.gettext("Property/ScenarioName", "")
            self.scenarioauthor = data.gettext("Property/ScenarioAuthor", "")
            self.dpath = data.getattr("Materials", "dpath", "")
            self.fpaths = []
            if self.dpath:
                for e in data.getfind("Materials"):
                    if e.text:
                        self.fpaths.append(e.text)

    @staticmethod
    def create_header(debuglog: Optional["cw.debug.logging.DebugLog"]) -> "SavedJPDCImageHeader":
        """シナリオ終了時にTempFileにある保存済みJPDCイメージを
        <Yado>/SavedJPDCImageに保存する。
        """
        assert cw.cwpy.ydata
        cw.cwpy.ydata.changed()
        cw.fsync.sync()
        savedjpdcimage = cw.util.join_paths(cw.cwpy.tempdir, "SavedJPDCImage")
        tempfilepath = cw.util.join_paths(cw.tempdir, "ScenarioLog/TempFile")

        # ヘッダを構築
        key = (cw.cwpy.sdata.name, cw.cwpy.sdata.author)
        header = cw.cwpy.ydata.savedjpdcimage.get(key, None)
        if header:
            header.remove_all()
        else:
            header = SavedJPDCImageHeader()
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
                    relpath = cw.util.join_paths("Materials", relpathbase)
                    topath = cw.util.join_paths(sdpath, relpath)
                    dpath2 = os.path.dirname(topath)

                    if not os.path.isdir(dpath2):
                        os.makedirs(dpath2)
                    shutil.copy2(frompath, topath)
                    header.fpaths.append(relpathbase)
                    cw.cwpy.ydata.deletedpaths.discard(topath)

        if header.fpaths:
            # 情報ファイル作成
            fpath = cw.util.join_paths(sdpath, "SavedJPDCImage.xml")
            element = cw.data.make_element("SavedJPDCImage")
            prop = cw.data.make_element("Property", "")
            e = cw.data.make_element("ScenarioName", cw.cwpy.sdata.name)
            prop.append(e)
            e = cw.data.make_element("ScenarioAuthor", cw.cwpy.sdata.author)
            prop.append(e)
            element.append(prop)
            mates = cw.data.make_element("Materials", "", attrs={"dpath": header.dpath})
            for mfpath in header.fpaths:
                e = cw.data.make_element("Material", mfpath)
                mates.append(e)
                if debuglog:
                    debuglog.add_jpdcimage(mfpath)
            element.append(mates)
            # ファイル書き込み
            etree = cw.data.xml2etree(element=element)
            etree.write_file(fpath)
            cw.cwpy.ydata.deletedpaths.discard(fpath)
            header.fpath = fpath

            cw.cwpy.ydata.savedjpdcimage[key] = header

        elif key in cw.cwpy.ydata.savedjpdcimage:
            # 保存された素材がない場合は削除
            del cw.cwpy.ydata.savedjpdcimage[key]

        return header

    def remove_all(self) -> None:
        """このオブジェクトで管理中の
        保存済みJPDCイメージを全て削除する。
        """
        assert cw.cwpy.ydata
        cw.cwpy.ydata.changed()
        cw.fsync.sync()
        dpath1 = cw.util.join_paths(cw.cwpy.yadodir, "SavedJPDCImage", self.dpath)
        dpath2 = cw.util.join_paths(cw.cwpy.tempdir, "SavedJPDCImage", self.dpath)
        for dpath3 in (dpath1, dpath2):
            if os.path.isdir(dpath3):
                for dpath, dnames, fnames in os.walk(dpath3):
                    for fname in fnames:
                        fpath = cw.util.join_paths(dpath, fname)
                        if os.path.isfile(fpath):
                            cw.cwpy.ydata.deletedpaths.add(fpath)


def enforce_str(value: Union[Optional[str], int, float, bool, Optional[bytes]]) -> str:
    assert isinstance(value, str), str(type(value))
    return value


def enforce_optional_str(value: Union[Optional[str], int, float, bool, Optional[bytes]]) -> Optional[str]:
    if isinstance(value, str):
        return value
    else:
        assert value is None, str(type(value)) + ":" + str(value)
        return value


def enforce_int(value: Union[Optional[str], int, float, bool, Optional[bytes]]) -> int:
    assert isinstance(value, int), str(type(value))
    return value


def enforce_float(value: Union[Optional[str], int, float, bool, Optional[bytes]]) -> float:
    assert isinstance(value, float), str(type(value))
    return value


def enforce_float_or_int(value: Union[Optional[str], int, float, bool, Optional[bytes]]) -> float:
    assert isinstance(value, (float, int)), str(type(value))
    return float(value)


def enforce_bool(value: Union[Optional[str], int, float, bool, Optional[bytes]]) -> bool:
    assert isinstance(value, bool), str(type(value))
    return value


def enforce_bytes(value: Union[Optional[str], int, float, bool, Optional[bytes]]) -> bytes:
    assert isinstance(value, bytes), str(type(value))
    return value


def enforce_optional_bytes(value: Union[Optional[str], int, float, bool, Optional[bytes]]) -> Optional[bytes]:
    if isinstance(value, bytes):
        return value
    else:
        # BUG: 空データがstrとして出てくる(Python 3.8.5)
        # assert value si None, str(type(value))
        assert not value, str(type(value))
        return None


class GetName(object):
    """XMLファイル中のProperty/Nameの内容を読む。"""
    def __init__(self, fpath: str, tagname: str = "Name") -> None:
        if fpath and cw.fsync.is_waiting(fpath):
            cw.fsync.sync()

        self.tagname = tagname
        self.name: str = ""
        self.stack: List[str] = []

        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.character_data

        with open(fpath, "rb") as f:
            try:
                parser.ParseFile(f)
            except Exception:
                pass
            f.close()

    def start_element(self, name: str, attrs: Dict[str, str]) -> None:
        self.stack.append(name)

    def end_element(self, name: str) -> None:
        if self.stack[1:] == ["Property"]:
            raise Exception()
        if self.stack[1:] == ["Property", self.tagname]:
            raise Exception()
        self.stack.pop()

    def character_data(self, data: str) -> None:
        if self.stack[1:] == ["Property", self.tagname]:
            self.name += data


class GetProperty(object):
    """XMLファイル中のProperty以下の内容を読む。"""
    def __init__(self, fpath: str = "", stream: Optional[BinaryIO] = None) -> None:
        if fpath and cw.fsync.is_waiting(fpath):
            cw.fsync.sync()

        self.properties: Dict[str, str] = {}
        self.attrs: Dict[Optional[str], Dict[str, str]] = {}
        self.stack: List[str] = []
        self.third: Dict[str, List[Tuple[str, Dict[str, str], str]]] = {}

        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = self.start_element
        parser.EndElementHandler = self.end_element
        parser.CharacterDataHandler = self.character_data

        if stream:
            try:
                parser.ParseFile(stream)
            except Exception:
                pass
        else:
            with open(fpath, "rb") as f:
                try:
                    parser.ParseFile(f)
                except Exception:
                    pass
                f.close()

    def start_element(self, name: str, attrs: Dict[str, str]) -> None:
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

    def end_element(self, name: str) -> None:
        if self.stack[1:] == ["Property"]:
            raise Exception()
        self.stack.pop()

    def character_data(self, data: str) -> None:
        if 2 < len(self.stack) and self.stack[1] == "Property":
            element = self.stack[2]
            if element not in self.properties:
                self.properties[element] = ""
            if 3 == len(self.stack):
                self.properties[element] += data
            if 4 == len(self.stack):
                seq = self.third[self.stack[2]]
                seq[-1] = (seq[-1][0], seq[-1][1], seq[-1][2] + data)


class GetRootAttribute(object):
    def __init__(self, fpath: str) -> None:
        """XMLファイル中のルート要素の属性を読む。"""
        if fpath and cw.fsync.is_waiting(fpath):
            cw.fsync.sync()

        self.attrs: Dict[str, str] = {}
        parser = xml.parsers.expat.ParserCreate()
        parser.StartElementHandler = self.start_element

        with open(fpath, "rb") as f:
            try:
                parser.ParseFile(f)
            except Exception:
                pass
            f.close()

    def start_element(self, name: str, attrs: Dict[str, str]) -> None:
        # ルート要素の属性
        self.attrs = attrs
        raise Exception()


class RaceHeader(object):
    def __init__(self, data: cw.data.CWPyElement) -> None:
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

        e_coeff = data.find("Coefficient")
        # レベル判定式に掛ける係数
        if e_coeff is not None and "level" in e_coeff.attrib:
            self.coeff_level: Optional[float] = e_coeff.getfloat(".", "level", 1.0)
        else:
            self.coeff_level = None
        # 1レベル毎のEP獲得量
        if e_coeff is not None and "ep" in e_coeff.attrib:
            self.coeff_ep: Optional[int] = e_coeff.getint(".", "ep", 10)
        else:
            self.coeff_ep = None

        self.coupons = []
        for e in data.getfind("Coupons"):
            name = e.gettext(".", "")
            value = e.getint(".", "value", 0)
            self.coupons.append((name, value))


class UnknownRaceHeader(RaceHeader):
    def __init__(self, setting: cw.setting.Setting) -> None:
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
        self.coeff_level: Optional[float] = None
        self.coeff_ep: Optional[int] = None
        self.coupons = []


def main() -> None:
    pass


if __name__ == "__main__":
    main()
