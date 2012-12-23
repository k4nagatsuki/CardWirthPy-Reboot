#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import re
import copy
import weakref
import StringIO
import wx

import cw


class CardHeader(object):
    def __init__(self, data=None, owner=None, carddata=None, from_scenario=False):
        self.ref_original = weakref.ref(self)
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
        self.keycodes.append(self.name)
        self.penalty = bool(u"ペナルティ" in self.keycodes)
        self.recycle = bool(u"リサイクル" in self.keycodes)
        self.uselimit = data.getint("UseLimit")
        self.target = data.gettext("Target")
        self.allrange = data.getbool("Target", "allrange")
        self.premium = data.gettext("Premium")
        physical = data.getattr("Ability", "physical").lower()
        mental = data.getattr("Ability", "mental").lower()
        self.vocation = (physical, mental)
        # カードの種類ごとに違う処理
        self.level = 0
        self.maxuselimit = 0
        self.price = 0
        self.hold = False
        self.enhance_avo = 0
        self.enhance_res = 0
        self.enhance_def = 0
        self.attachment = False

        if self.type == "SkillCard":
            self.level = data.getint("Level")
            self.hold = data.getbool("Hold")
        elif self.type == "ItemCard":
            self.maxuselimit = data.getint("UseLimit", "max")
            self.enhance_avo = data.getint("EnhanceOwner", "avoid")
            self.enhance_res = data.getint("EnhanceOwner", "resist")
            self.enhance_def = data.getint("EnhanceOwner", "defense")
            self.hold = data.getbool("Hold")
            self.price = data.getint("Price")
        elif self.type == "BeastCard":
            if data.hasfind("Attachment"):
                self.attachment = data.getbool("Attachment")
            elif self.is_ccardheader():
                self.attachment = True if self.uselimit == 0 else False
                e = cw.data.make_element("Attachment", str(self.attachment))
                data.append(e)

        # シナリオ取得フラグ
        if from_scenario or (self.carddata is not None and self.carddata.get("scenariocard")):
            self.scenariocard = True
        else:
            self.scenariocard = False

        # Image
        path = data.gettext("ImagePath", "")
        self.set_cardimg(path)
        # cardcontrolダイアログで使うフラグ
        self.negaflag = False
        self.clickedflag = False

        # 所持スキルカードだった場合は使用回数を設定
        if self.is_ccardheader() and self.type == "SkillCard":
            self.get_uselimit()

    def set_cardimg(self, path):
        if self.type == "ActionCard":
            path = cw.util.join_paths(cw.cwpy.skindir, path)
        elif self.scenariocard:
            if not cw.binary.image.path_is_code(path):
                path = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
        else:
            path = cw.util.join_yadodir(path)

        self.imgpath = path
        self.cardimg = cw.image.CardImage(self.imgpath, self.get_bgtype(),
                                                    self.name, self.premium)
        self.rect = self.cardimg.rect

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
        return self.type.upper().replace("CARD", "")

    def get_cardwxbmp(self):
        return self.cardimg.get_cardwxbmp(self)

    def get_cardimg(self):
        return self.cardimg.get_cardimg(self)

    def get_vocation_level(self):
        """
        適性値の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
        """
        value = self.get_vocation_val()

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

    def get_vocation_val(self):
        """
        適性値(身体特性+精神特性の合計値)を返す。
        """
        owner = self.get_owner()
        physical = self.vocation[0]
        mental = self.vocation[1].replace("un", "", 1)
        physical = owner.data.getint("/Property/Ability/Physical", physical)
        mental = owner.data.getint("/Property/Ability/Mental", mental)

        if self.vocation[1].startswith("un"):
            mental = -mental

        return physical + mental

    def get_uselimit_level(self):
        """
        使用回数の段階値を返す。段階値は(0 > 1 > 2 > 3 > 4)の順
        """
        limit, maxlimit = self.get_uselimit()
        limitper = 100 * limit / maxlimit

        if limitper == 100:
            value = 4
        elif 100 > limitper >=  66:
            value = 3
        elif 66 > limitper >= 33:
            value = 2
        elif 33 > limitper > 0:
            value = 1
        elif limitper ==   0:
            value = 0

        return value

    def get_uselimit(self):
        """
        (使用回数, 最大使用回数)を返す。
        """
        if self.is_ccardheader() and self.type == "SkillCard"\
                                                    and not self.maxuselimit:
            owner = self.get_owner()
            level = owner.data.getint("/Property/Level")
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
                    not isinstance(self.get_owner(), cw.character.Player):
                self.uselimit = self.maxuselimit

        return self.uselimit, self.maxuselimit

    def get_enhance_val(self):
        """
        カード所持時に設定されている強化値を、
        (回避値, 抵抗値, 防御値)の順のタプルで返す。
        """
        if self.type == "ItemCard":
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
            if header.uselimit <= 0 and not header.recycle:
                if cw.cwpy.battle and header in owner.deck.hand:
                    owner.deck.hand.remove(header)

                cw.cwpy.trade("TRASHBOX", header=header, from_event=True)

        # 召喚獣カード。
        elif header.type == "BeastCard" and not self.attachment:
            header.uselimit += value
            header.uselimit = cw.util.numwrap(header.uselimit, 0, 999)
            e = header.carddata.getfind("Property/UseLimit")
            e.text = str(header.uselimit)
            owner.data.is_edited = True

            # カード消滅処理
            if header.uselimit <= 0:
                # 召喚獣消去効果で消えてる場合もあるのでチェック
                if header in owner.cardpocket[cw.POCKET_BEAST]:
                    cw.cwpy.trade("TRASHBOX", header=header, from_event=True)

    def write(self):
        if self.carddata is None:
            return

        if self.fpath:
            path = self.fpath
        else:
            fname = cw.util.repl_dischar(self.name) + ".xml"
            path = cw.util.join_paths(cw.cwpy.tempdir, self.type, fname)
            self.fpath = cw.util.dupcheck_plus(path)

        etree = cw.data.xml2etree(element=self.carddata)

        if not self.type == "BeastCard":
            etree.edit("/Property/Hold", "False")

        etree.write(self.fpath)
        # self.fpathを削除予定のfpathリストから削除
        cw.cwpy.ydata.deletedpaths.discard(self.fpath)

    def contain_xml(self):
        if self.carddata is None:
            e = cw.data.yadoxml2etree(self.fpath)
            self.carddata = e.getroot()
            # self.fpathを削除予定のfpathリストに追加
            cw.cwpy.ydata.deletedpaths.add(self.fpath)

    def set_scenariostart(self):
        """
        シナリオ開始時に呼ばれる。
        """
        if self.is_ccardheader() and self.type == "SkillCard":
            e = self.carddata.getfind("Property/UseLimit")
            e.text = str(self.uselimit)
            owner = self.get_owner()
            owner.data.is_edited = True
        elif self.is_backpackheader() and self.scenariocard:
            path = self.carddata.gettext("Property/ImagePath", "")
            self.set_cardimg(path)

    def set_scenarioend(self):
        """
        シナリオ終了時に呼ばれる。
        非付帯召喚カードを削除したり、
        シナリオで取得したカードの素材ファイルを宿にコピーしたりする。
        """
        if self.scenariocard:
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
            self.set_cardimg(path)
        elif self.type == "BeastCard" and not self.attachment:
            cw.cwpy.trade("TRASHBOX", header=self, from_event=True)

        if self.is_ccardheader() and self.type == "SkillCard":
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
        header.cardimg = cw.image.CardImage(self.imgpath, self.get_bgtype(),
                                                    self.name, self.premium)
        header.rect = header.cardimg.rect
        return header

    def is_ccardheader(self):
        return bool(isinstance(self._owner, weakref.ref))

    def is_backpackheader(self):
        return bool(self._owner == "BACKPACK")

    def is_storehouseheader(self):
        return bool(self._owner == "STOREHOUSE")

    def is_autoselectable(self):
        if self.type == "BeastCard":
            flag = not bool(self.target == "None")
        else:
            flag = not self.hold

            if self.type == "ItemCard":
                flag &= not bool(self.recycle and self.uselimit <= 0)

        return flag

    def get_targets(self):
        """
        (ターゲットのリスト, 効果のあるターゲットのリスト)を返す。
        """
        owner = self.get_owner()

        if self.target == "Both":
            targets = cw.cwpy.get_pcards("unreversed")
            targets.extend(cw.cwpy.get_ecards("unreversed"))
        elif self.target == "Party":
            if isinstance(owner, cw.character.Enemy):
                targets = cw.cwpy.get_ecards("unreversed")
            else:
                targets = cw.cwpy.get_pcards("unreversed")

        elif self.target == "Enemy":
            if isinstance(owner, cw.character.Enemy):
                targets = cw.cwpy.get_pcards("unreversed")
            else:
                targets = cw.cwpy.get_ecards("unreversed")

        elif self.target == "User":
            targets = [owner]
        elif self.target == "None":
            targets = []

        if not self.allrange:
            targets = [target for target in targets if target.is_alive()]

        return targets, cw.effectmotion.get_effectivetargets(self, targets)

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
        if not cw.binary.image.path_is_code(path):
            path = cw.util.join_paths(cw.cwpy.sdata.scedir, path)
        self.cardimg = cw.image.CardImage(path, "INFO", self.name)
        self.rect = self.cardimg.rect
        # cardcontrolダイアログで使うフラグ
        self.negaflag = False
        self.clickedflag = False

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
    def __init__(self, data, album=False):
        """
        album: アルバム用の場合はTrueにする。
        冒険者のヘッダ。引数のdataはPropertyElement。
        """
        self.fpath = data.fpath
        self.level = data.getint("Level", 0)
        self.name = data.gettext("Name", "")
        self.imgpath = data.gettext("ImagePath", "")
        self.album = album

        # シナリオプレイ中にロストしたかどうかのフラグ
        if data.hasfind("", "lost"):
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

        for e in data.getfind("/Property/Coupons"):
            if not e.text:
                continue

            # EP減少
            if e.text == u"＠ＥＰ":
                e.attrib["value"] = str(e.getint("", "value") - n)
            # 子作り回数加算
            elif r_gene.match(e.text):
                e.attrib["value"] = str(e.getint("", "value") + 1)

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
                for index in range(len(nature.genepattern)):
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

    def rotate_right(self):
        # 母親の遺伝情報のローテートは一周のみ
        count = cw.util.numwrap(self.count + 1, 1, 10) % 10
        bits = self.bits[count:]
        bits.extend(self.bits[:count])
        return Gene(bits)

    def rotate_left(self):
        count = self.count + 1 % 10
        bits = self.bits[count:]
        bits.extend(self.bits[:count])
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
                f = io.BytesIO(str(self.image))
                image = wx.ImageFromStream(f)
                f.close()
                self._wxbmp = cw.util.load_wxbmp(image=image, mask=mask)
            else:
                self._wxbmp = wx.EmptyBitmap(0, 0)
        return self._wxbmp

class PartyHeader(object):
    def __init__(self, data):
        """
        data: PartyのPropetyElement
        """
        self.fpath = data.fpath
        self.name = data.gettext("Name")
        self.money = data.getint("Money", 0)
        self.members = [e.text for e in data.getfind("Members") if e.text]

    def is_adventuring(self):
        path = os.path.splitext(self.fpath)[0] + ".wsl"
        return bool(cw.util.get_yadofilepath(path))

    def remove_adventuring(self):
        path = os.path.splitext(self.fpath)[0] + ".wsl"
        cw.cwpy.ydata.deletedpaths.add(path)

    def get_sceheader(self):
        """
        現在冒険中のシナリオのScenarioHeaderを返す。
        """
        path = os.path.splitext(self.fpath)[0] + ".wsl"
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
        seq = []

        for fname in self.members:
            fname = fname + ".xml"
            path = cw.util.join_paths(cw.cwpy.yadodir, "Adventurer", fname)
            seq.append(path)

        return seq

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
            name = e.gettext("", "")
            value = 0
            self.coupons.append((name, value))

class UnknownRaceHeader(RaceHeader):
    def __init__(self):
        self.name = u"―未指定―"
        self.desc = (u"種族を指定せず、キャラクターを作成する。\n" +
                     u"初期能力値や特性は標準のものを採用する。")
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
