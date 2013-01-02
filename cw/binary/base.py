#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import weakref

import util
import xmltemplate

import cw.binary.image


class CWBinaryBase(object):
    def __init__(self, parent, f, yadodata=False, materialdir="Material", image_export=True):
        self.set_root(parent)
        self.xmltype = self.__class__.__name__
        if hasattr(f, "name"):
            self.fpath = f.name
        else:
            self.fpath = ""
        self.set_materialdir(materialdir)
        self.set_image_export(image_export)

        if parent:
            self._yadodata = parent._yadodata
        else:
            self._yadodata = yadodata

    def set_root(self, parent):
        if parent:
            self._root = parent._root
        else:
            self._root = weakref.ref(self)

    def get_root(self):
        return self._root()

    def set_dir(self, path):
        self.get_root()._dir = path

    def get_dir(self):
        try:
            return self.get_root()._dir
        except:
            return ""

    def set_imgdir(self, path):
        self.get_root()._imgdir = path

    def get_imgdir(self):
        try:
            return self.get_root()._imgdir
        except:
            return ""

    def get_fname(self):
        fname = os.path.basename(self.fpath)
        return os.path.splitext(fname)[0]

    def is_root(self):
        return bool(self == self.get_root())

    def is_yadodata(self):
        return self._yadodata

    def set_materialdir(self, materialdir):
        """materialdirを素材ディレクトリとして登録する。
        デフォルト値は"Material"。"""
        self._materialdir = materialdir

    def get_materialdir(self):
        """素材ディレクトリ名を返す。
        親要素がある場合、親の設定が優先される。"""
        root = self.get_root()
        if root is self:
            return self._materialdir
        else:
            return root.get_materialdir()

    def set_image_export(self, image_export):
        """XML変換時に格納イメージをエクスポートするか設定する。"""
        self._image_export = image_export

    def get_image_export(self):
        """XML変換時に格納イメージをエクスポートする場合はTrue。
        親要素がある場合、親の設定が優先される。"""
        root = self.get_root()
        if root is self:
            return self._image_export
        else:
            return root.get_image_export()


#-------------------------------------------------------------------------------
# XML作成用
#-------------------------------------------------------------------------------

    def create_xml(self, dpath):
        """XMLファイルを作成する。
        dpath: XMLを作成するディレクトリ
        """
        # 保存ディレクトリ設定
        self.set_dir(dpath)
        # xml文字列取得
        xmltext = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xmltext += self.get_xmltext(0)

        # xmlファイルパス
        if self.xmltype in ("Summary", "Environment"):
            path = util.join_paths(self.get_dir(), self.xmltype + ".xml")
        else:
            name = util.check_filename(self.name) + ".xml"

            # シナリオデータは先頭にidを付与
            if not self.is_yadodata():
                name = str(self.id).zfill(2) + "_" + name

            path = util.join_paths(self.get_dir(), self.xmltype, name)

        # xml出力
        path = util.check_duplicate(path)

        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        f = open(path, "wb")
        f.write(xmltext.encode("utf-8"))
        f.close()

    def export_image(self):
        """内部画像を出力する"""
        if not hasattr(self, "image"):
            return ""

        if not self.image:
            return ""

        if not self.get_image_export():
            # パスの代わりにバイナリイメージを使用する
            return cw.binary.image.data_to_code(self.image)

        # 画像保存ディレクトリ
        if self.xmltype == "Summary":
            imgdir = self.get_dir()
        elif self.xmltype == "BeastCard" and self.summoneffect:
            imgdir = self.get_imgdir()

            if not imgdir:
                root = self.get_root()
                name = util.check_filename(root.name)
                mdir = self.get_materialdir()
                if mdir == "":
                    imgdir = util.join_paths(self.get_dir(), root.xmltype, name)
                else:
                    imgdir = util.join_paths(self.get_dir(), mdir, root.xmltype, name)
                imgdir = util.check_duplicate(imgdir)
                self.set_imgdir(imgdir)

        elif self.xmltype in ("Adventurer", "SkillCard", "ItemCard",
                                                    "BeastCard", "CastCard"):
            name = util.check_filename(self.name)
            mdir = self.get_materialdir()
            if mdir == "":
                imgdir = util.join_paths(self.get_dir(), self.xmltype, name)
            else:
                imgdir = util.join_paths(self.get_dir(), mdir, self.xmltype, name)
            imgdir = util.check_duplicate(imgdir)
            self.set_imgdir(imgdir)
        else:
            mdir = self.get_materialdir()
            if mdir == "":
                imgdir = util.join_paths(self.get_dir(), self.xmltype)
            else:
                imgdir = util.join_paths(self.get_dir(), mdir, self.xmltype)

        # 画像保存
        # 画像パス
        if self.xmltype == "Summary":
            path = util.join_paths(imgdir, self.xmltype + ".bmp")
        else:
            name = util.check_filename(self.name) + ".bmp"
            path = util.join_paths(imgdir, name)

        # 画像出力
        path = util.check_duplicate(path)

        if not os.path.isdir(imgdir):
            os.makedirs(imgdir)

        f = open(path, "wb")
        f.write(self.image)
        f.close()
        # 最後に参照パスを返す
        path = path.replace(self.get_dir() + "/", "", 1)
        return util.repl_escapechar(path)

    def get_xmldict(self, indent):
        """XML作成用の辞書を返す。"""
        return {}

    def get_xmltext(self, indent):
        """XML作成用の文字列を返す。"""
        imgpath = self.export_image()
        d = self.get_xmldict(indent)

        if not d.get("imgpath"):
            d["imgpath"] = imgpath

        return xmltemplate.get_xmltext(self.xmltype, d)

    def get_childrentext(self, children, indent):
        """子エレメントのXML作成用の文字列を返す。
        children: 子エレメントのリスト
        """
        if children:
            seq = [child.get_xmltext(indent) for child in children]
            return "\n" + "\n".join(seq)
        else:
            return ""

    def get_materialpath(self, path):
        """引数のパスを素材ディレクトリに関連づける。
        dpath: 素材ファイルのパス。
        """
        if path == u"（なし）":
            return ""
        mdir = self.get_materialdir()
        if mdir == "":
            return path
        elif path:
            return util.join_paths(mdir, path)
        else:
            return ""

    def get_indent(self, indent):
        """インデントの文字列を返す。スペース一個分。"""
        return " " * indent

    def get_propertiestext(self, d):
        """XMLエレメントのプロパティ文字列を返す。"""
        s = ""

        for key, value in d.iteritems():
            s += ' %s="%s"' % (key, value)

        return s

#-------------------------------------------------------------------------------
# コンテント
#-------------------------------------------------------------------------------

    def conv_contenttype(self, n):
        """引数の値から、コンテントの種類を返す。"""
        if n == 0:
            return "Start", ""                # スタート
        elif n == 1:
            return "Link", "Start"            # スタートへのリンク
        elif n == 2:
            return "Start", "Battle"          # バトル開始
        elif n == 3:
            return "End", ""                  # シナリオクリア
        elif n == 4:
            return "End", "BadEnd"            # ゲームオーバー
        elif n == 5:
            return "Change", "Area"           # エリア移動
        elif n == 6:
            return "Talk", "Message"          # メッセージ
        elif n == 7:
            return "Play", "Bgm"              # BGM変更
        elif n == 8:
            return "Change", "BgImage"        # 背景変更
        elif n == 9:
            return "Play", "Sound"            # 効果音
        elif n == 10:
            return "Wait", ""                 # 空白時間
        elif n == 11:
            return "Effect", ""               # 効果
        elif n == 12:
            return "Branch", "Select"         # メンバ選択分岐
        elif n == 13:
            return "Branch", "Ability"        # 能力判定分岐
        elif n == 14:
            return "Branch", "Random"         # ランダム分岐
        elif n == 15:
            return "Branch", "Flag"           # フラグ分岐
        elif n == 16:
            return "Set", "Flag"              # フラグ変更
        elif n == 17:
            return "Branch", "MultiStep"      # ステップ多岐分岐
        elif n == 18:
            return "Set", "Step"              # ステップ変更
        elif n == 19:
            return "Branch", "Cast"           # キャスト存在分岐
        elif n == 20:
            return "Branch", "Item"           # アイテム所持分岐
        elif n == 21:
            return "Branch", "Skill"          # スキル所持分岐
        elif n == 22:
            return "Branch", "Info"           # 情報所持分岐
        elif n == 23:
            return "Branch", "Beast"          # 召喚獣存在分岐
        elif n == 24:
            return "Branch", "Money"          # 所持金分岐
        elif n == 25:
            return "Branch", "Coupon"         # 称号分岐
        elif n == 26:
            return "Get", "Cast"              # キャスト加入
        elif n == 27:
            return "Get", "Item"              # アイテム入手
        elif n == 28:
            return "Get", "Skill"             # スキル入手
        elif n == 29:
            return "Get", "Info"              # 情報入手
        elif n == 30:
            return "Get", "Beast"             # 召喚獣獲得
        elif n == 31:
            return "Get", "Money"             # 所持金増加
        elif n == 32:
            return "Get", "Coupon"            # 称号付与
        elif n == 33:
            return "Lose", "Cast"             # キャスト離脱
        elif n == 34:
            return "Lose", "Item"             # アイテム喪失
        elif n == 35:
            return "Lose", "Skill"            # スキル喪失
        elif n == 36:
            return "Lose", "Info"             # 情報喪失
        elif n == 37:
            return "Lose", "Beast"            # 召喚獣喪失
        elif n == 38:
            return "Lose", "Money"            # 所持金減少
        elif n == 39:
            return "Lose", "Coupon"           # 称号剥奪
        elif n == 40:
            return "Talk", "Dialog"           # セリフ
        elif n == 41:
            return "Set", "StepUp"            # ステップ増加
        elif n == 42:
            return "Set", "StepDown"          # ステップ減少
        elif n == 43:
            return "Reverse", "Flag"          # フラグ反転
        elif n == 44:
            return "Branch", "Step"           # ステップ上下分岐
        elif n == 45:
            return "Elapse", "Time"           # 時間経過
        elif n == 46:
            return "Branch", "Level"          # レベル分岐
        elif n == 47:
            return "Branch", "Status"         # 状態分岐
        elif n == 48:
            return "Branch", "PartyNumber"    # 人数判定分岐
        elif n == 49:
            return "Show", "Party"            # パーティ表示
        elif n == 50:
            return "Hide", "Party"            # パーティ隠蔽
        elif n == 51:
            return "Effect", "Break"          # 効果中断
        elif n == 52:
            return "Call", "Start"            # スタートのコール
        elif n == 53:
            return "Link", "Package"          # パッケージへのリンク
        elif n == 54:
            return "Call", "Package"          # パッケージのコール
        elif n == 55:
            return "Branch", "Area"           # エリア分岐
        elif n == 56:
            return "Branch", "Battle"         # バトル分岐
        elif n == 57:
            return "Branch", "CompleteStamp"  # 終了シナリオ分岐
        elif n == 58:
            return "Get", "CompleteStamp"     # 終了シナリオ設定
        elif n == 59:
            return "Lose", "CompleteStamp"    # 終了シナリオ削除
        elif n == 60:
            return "Branch", "Gossip"         # ゴシップ分岐
        elif n == 61:
            return "Get", "Gossip"            # ゴシップ追加
        elif n == 62:
            return "Lose", "Gossip"           # ゴシップ削除
        elif n == 63:
            return "Branch", "IsBattle"       # バトル判定分岐
        elif n == 64:
            return "Redisplay", ""            # 画面の再構築
        elif n == 65:
            return "Check", "Flag"            # フラグ判定
        else:
            raise ValueError(self.fpath)

#-------------------------------------------------------------------------------
# 適用メンバ・適用範囲
#-------------------------------------------------------------------------------

    def conv_target_member(self, n):
        """引数の値から、「適用メンバ」の種類を返す。
        0:Selected(現在選択中のメンバ), 1:Random(ランダムメンバ),
        2:Unselected(現在選択中以外のメンバ)
        睡眠者有効ならば＋3で、返り値の文字列の後ろに"Sleep"を付ける。
        さらに6:Party(パーティの全員。効果コンテントの時に使う)
        """
        if n == 0:
            return "Selected"
        elif n == 1:
            return "Random"
        elif n == 2:
            return "Unselected"
        elif n == 3:
            return "SelectedSleep"
        elif n == 4:
            return "RandomSleep"
        elif n == 5:
            return "PartySleep"
        elif n == 6:
            return "Party"
        else:
            raise ValueError(self.fpath)

    def conv_target_scope(self, n):
        """引数の値から、「適用範囲」の種類を返す。
        0:Selected(現在選択中のメンバ), 1:Random(パーティの誰か一人),
        2:Party(パーティの全員), 3:Backpack(荷物袋),
        4:PartyAndBackpack(全体(荷物袋含む)) 5:Field(フィールド全体)
        """
        if n == 0:
            return "Selected"
        elif n == 1:
            return "Random"
        elif n == 2:
            return "Party"
        elif n == 3:
            return "Backpack"
        elif n == 4:
            return "PartyAndBackpack"
        elif n == 5:
            return "Field"
        else:
            raise ValueError(self.fpath)

#-------------------------------------------------------------------------------
# コンテント系
#-------------------------------------------------------------------------------

    def conv_spreadtype(self, n):
        """引数の値から、カードの並べ方を返す。"""
        if n == 0:
            return "Auto"
        elif n == 1:
            return "Custom"
        else:
            raise ValueError(self.fpath)

    def conv_statustype(self, n):
        """引数の値から、状態を返す。
        0:Active(行動可能), 1:Inactive(行動不可), 2:Alive(生存), 3:Dead(非生存),
        4:Fine(健康), 5:Injured(負傷), 6:Heavy-Injured(重傷),
        7:Unconscious(意識不明), 8:Poison(中毒), 9:Sleep(眠り),
        10:Bind(呪縛), 11:Paralyze(麻痺・石化)
        """
        if n == 0:
            return "Active"
        elif n == 1:
            return "Inactive"
        elif n == 2:
            return "Alive"
        elif n == 3:
            return "Dead"
        elif n == 4:
            return "Fine"
        elif n == 5:
            return "Injured"
        elif n == 6:
            return "HeavyInjured"
        elif n == 7:
            return "Unconscious"
        elif n == 8:
            return "Poison"
        elif n == 9:
            return "Sleep"
        elif n == 10:
            return "Bind"
        elif n == 11:
            return "Paralyze"
        else:
            raise ValueError(self.fpath)

#-------------------------------------------------------------------------------
# 効果モーション関連
#-------------------------------------------------------------------------------

    def conv_effectmotion_element(self, n):
        """引数の値から、効果モーションの「属性」を返す。
        0:All(全), 1:Health(肉体), 2:Mind(精神), 3:Miracle(神聖),
        4:Magic(魔力), 5:Fire(炎), 6:Ice(冷)
        """
        if n == 0:
            return "All"
        elif n == 1:
            return "Health"
        elif n == 2:
            return "Mind"
        elif n == 3:
            return "Miracle"
        elif n == 4:
            return "Magic"
        elif n == 5:
            return "Fire"
        elif n == 6:
            return "Ice"
        else:
            raise ValueError(self.fpath)

    def conv_effectmotion_type(self, tabn, n):
        """引数の値から、効果モーションの「種類」を返す。
        tabn: 大分類。
        n: 小分類。
        """
        if tabn == 0:
            if n == 0:
                return "Heal"                     # 回復
            elif n == 1:
                return "Damage"                   # ダメージ
            elif n == 2:
                return "Absorb"                   # 吸収
            else:
                raise ValueError(self.fpath)

        elif tabn == 1:
            if n == 0:
                return "Paralyze"                 # 麻痺状態
            elif n == 1:
                return "DisParalyze"              # 麻痺解除
            elif n == 2:
                return "Poison"                   # 中毒状態
            elif n == 3:
                return "DisPoison"                # 中毒解除
            else:
                raise ValueError(self.fpath)

        elif tabn == 2:
            if n == 0:
                return "GetSkillPower"            # 精神力回復
            elif n == 1:
                return "LoseSkillPower"           # 精神力不能
            else:
                raise ValueError(self.fpath)

        elif tabn == 3:
            if n == 0:
                return "Sleep"                    # 睡眠状態
            elif n == 1:
                return "Confuse"                  # 混乱状態
            elif n == 2:
                return "Overheat"                 # 激昂状態
            elif n == 3:
                return "Brave"                    # 勇敢状態
            elif n == 4:
                return "Panic"                    # 恐慌状態
            elif n == 5:
                return "Normal"                   # 正常状態
            else:
                raise ValueError(self.fpath)

        elif tabn == 4:
            if n == 0:
                return "Bind"                     # 束縛状態
            elif n == 1:
                return "DisBind"                  # 束縛解除
            elif n == 2:
                return "Silence"                  # 沈黙状態
            elif n == 3:
                return "DisSilence"               # 沈黙解除
            elif n == 4:
                return "FaceUp"                   # 暴露状態
            elif n == 5:
                return "FaceDown"                 # 暴露解除
            elif n == 6:
                return "AntiMagic"                # 魔法無効化状態
            elif n == 7:
                return "DisAntiMagic"             # 魔法無効化解除
            else:
                raise ValueError(self.fpath)

        elif tabn == 5:
            if n == 0:
                return "EnhanceAction"            # 行動力変化
            elif n == 1:
                return "EnhanceAvoid"             # 回避力変化
            elif n == 2:
                return "EnhanceResist"            # 抵抗力変化
            elif n == 3:
                return "EnhanceDefense"           # 防御力変化
            else:
                raise ValueError(self.fpath)

        elif tabn == 6:
            if n == 0:
                return "VanishTarget"             # 対象消去
            elif n == 1:
                return "VanishCard"               # カード消去
            elif n == 2:
                return "VanishBeast"              # 召喚獣消去
            else:
                raise ValueError(self.fpath)

        elif tabn == 7:
            if n == 0:
                return "DealAttackCard"           # 通常攻撃
            elif n == 1:
                return "DealPowerfulAttackCard"   # 渾身の一撃
            elif n == 2:
                return "DealCriticalAttackCard"   # 会心の一撃
            elif n == 3:
                return "DealFeintCard"            # フェイント
            elif n == 4:
                return "DealDefenseCard"          # 防御
            elif n == 5:
                return "DealDistanceCard"         # 見切り
            elif n == 6:
                return "DealConfuseCard"          # 混乱
            elif n == 7:
                return "DealSkillCard"            # 特殊技能
            else:
                raise ValueError(self.fpath)

        elif tabn == 8:
            if n == 0:
                return "SummonBeast"              # 召喚獣召喚
            else:
                raise ValueError(self.fpath)

        else:
            raise ValueError(self.fpath)

    def conv_effectmotion_damagetype(self, n):
        """引数の値から、効果モーションの「属性」を返す。
        0:levelratio(レベル比), 1:normal(効果値), 2:max(最大値)
        """
        if n == 0:
            return "LevelRatio"
        elif n == 1:
            return "Normal"
        elif n == 2:
            return "Max"
        else:
            raise ValueError(self.fpath)

#-------------------------------------------------------------------------------
# スキル・アイテム・召喚獣関連
#-------------------------------------------------------------------------------

    def conv_card_effecttype(self, n):
        """引数の値から、「効果属性」の種類を返す。
        0:Physic(物理属性), 1:Magic(魔法属性), 2:MagicalPhysic(魔法的物理属性),
        3:PhysicalMagic(物理的魔法属性), 4:None(無属性)
        """
        if n == 0:
            return "Physic"
        elif n == 1:
            return "Magic"
        elif n == 2:
            return "MagicalPhysic"
        elif n == 3:
            return "PhysicalMagic"
        elif n == 4:
            return "None"
        else:
            raise ValueError(self.fpath)

    def conv_card_resisttype(self, n):
        """引数の値から、「抵抗属性」の種類を返す。
        0:Avoid(物理属性), 1:Resist(抵抗属性), 3:Unfail(必中属性)
        """
        if n == 0:
            return "Avoid"
        elif n == 1:
            return "Resist"
        elif n == 2:
            return "Unfail"
        else:
            raise ValueError(self.fpath)

    def conv_card_visualeffect(self, n):
        """引数の値から、「視覚的効果」の種類を返す。
        0:None(無し), 1:Reverse(反転),
        2:Horizontal(横), 3:Vertical(縦)
        """
        if n == 0:
            return "None"
        elif n == 1:
            return "Reverse"
        elif n == 2:
            return "Horizontal"
        elif n == 3:
            return "Vertical"
        else:
            raise ValueError(self.fpath)

    def conv_card_physicalability(self, n):
        """引数の値から、身体的要素の種類を返す。
        0:Dex(器用), 1:Agl(素早さ), 2:Int(知力)
        3:Str(筋力), 4:Vit(生命), 5:Min(精神)
        """
        if n == 0:
            return "Dex"
        elif n == 1:
            return "Agl"
        elif n == 2:
            return "Int"
        elif n == 3:
            return "Str"
        elif n == 4:
            return "Vit"
        elif n == 5:
            return "Min"
        else:
            raise ValueError(self.fpath)

    def conv_card_mentalability(self, n):
        """引数の値から、精神的要素の種類を返す。
        1:Aggressive(好戦), -1:Unaggressive(平和), 2:Cheerful(社交),
        -2:Uncheerful(内向), 3:Brave(勇敢), -3:Unbrave(臆病), 4:Cautious(慎重),
        -4:Uncautious(大胆), 5:Trickish(狡猾), -5:Untrickish(正直)
        """
        if n == 1:
            return "Aggressive"
        elif n == -1:
            return "Unaggressive"
        elif n == 2:
            return "Cheerful"
        elif n == -2:
            return "Uncheerful"
        elif n == 3:
            return "Brave"
        elif n == -3:
            return "Unbrave"
        elif n == 4:
            return "Cautious"
        elif n == -4:
            return "Uncautious"
        elif n == 5:
            return "Trickish"
        elif n == -5:
            return "Untrickish"
        else:
            raise ValueError(self.fpath)

    def conv_card_target(self, n):
        """引数の値から、効果目標の種類を返す。
        0:None(対象無し), 1:User(使用者), 2:Party(味方),
        3:Enemy(敵方) ,4:Both(双方)
        """
        if n == 0:
            return "None"
        elif n == 1:
            return "User"
        elif n == 2:
            return "Party"
        elif n == 3:
            return "Enemy"
        elif n == 4:
            return "Both"
        else:
            raise ValueError(self.fpath)

    def conv_card_premium(self, n):
        """引数の値から、希少度の種類を返す。
        一時的に所持しているだけのF9でなくなるカードの場合は+3されている。
        0:Normal, 2:Rare, 1:Premium
        """
        if n == 0:
            return "Normal"
        elif n == 1:
            return "Rare"
        elif n == 2:
            return "Premium"
        else:
            raise ValueError(self.fpath)

#-------------------------------------------------------------------------------
#　キャラクター関連
#-------------------------------------------------------------------------------

    def conv_mentality(self, n):
        """引数の値から、精神状態の種類を返す。
        ここでは「"0"=正常状態」以外の判別は適当。
        """
        if n == 0:
            return "Normal"            # 正常状態
        elif n == 1:
            return "Panic"             # 恐慌状態
        elif n == 2:
            return "Brave"             # 勇敢状態
        elif n == 3:
            return "Overheat"          # 激昂状態
        elif n == 4:
            return "Confuse"           # 混乱状態
        elif n == 5:
            return "Sleep"             # 睡眠状態
        else:
            raise ValueError(self.fpath)

#-------------------------------------------------------------------------------
#　宿データ関連
#-------------------------------------------------------------------------------

    def conv_yadotype(self, n):
        """引数の値から、宿の種類を返す。
        1:Normal(ノーマル宿), 2:Debug(デバッグ宿)
        """
        if n == 1:
            return "Normal"
        elif n == 2:
            return "Debug"
        else:
            raise ValueError(self.fpath)

    def conv_yado_summaryview(self, n):
        """引数の値から、張り紙の表示の種類を返す。
        0:隠蔽シナリオ、終了済シナリオを表示しない, 1:隠蔽シナリオを表示しない,
        2:全てのシナリオを表示, 3:適応レベルのシナリオのみを表示
        """
        if n == 0:
            return "HideHiddenAndCompleteScenario"
        elif n == 1:
            return "HideHiddenScenario"
        elif n == 2:
            return "ShowAll"
        elif n == 3:
            return "ShowFittingScenario"
        else:
            raise ValueError(self.fpath)

    def conv_yado_bgchange(self, n):
        """引数の値から、背景の切り替え方式の種類を返す。
        0:アニメーションなし, 1:短冊式,
        2:色変換式, 3:ドット置換式
        """
        if n == 0:
            return "NoAnimation"
        elif n == 1:
            return "ReedShape"
        elif n == 2:
            return "ColorShade"
        elif n == 3:
            return "ReplaceDot"
        else:
            raise ValueError(self.fpath)

def main():
    pass

if __name__ == "__main__":
    main()

