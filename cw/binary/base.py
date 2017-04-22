#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import io
import weakref

import util
import wx

import cw


class CWBinaryBase(object):
    def __init__(self, parent, f, yadodata=False, materialdir="Material", image_export=True):
        self.set_root(parent)
        self.xmltype = self.__class__.__name__
        if hasattr(f, "name"):
            self.fpath = f.name
        else:
            self.fpath = ""
        self.materialbasedir = ""
        self.set_materialdir(materialdir)
        self.set_image_export(image_export, False)
        self.yadodb = None
        self.xmlpath = ""

        if parent:
            self.yadodata = parent.yadodata
        else:
            self.yadodata = yadodata

    def set_root(self, parent):
        if parent:
            self.root = parent.root
        else:
            self.root = weakref.ref(self)

    def get_root(self):
        return self.root()

    def set_dir(self, path):
        self.get_root().dir = path

    def get_dir(self):
        try:
            return self.get_root().dir
        except:
            return ""

    def set_imgdir(self, path):
        self.get_root().imgdir = path

    def get_imgdir(self):
        try:
            return self.get_root().imgdir
        except:
            return ""

    def get_fname(self):
        fname = os.path.basename(self.fpath)
        return cw.util.splitext(fname)[0]

    def is_root(self):
        return bool(self == self.get_root())

    def is_yadodata(self):
        return self.yadodata

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

    def set_image_export(self, image_export, force=False):
        """XML変換時に格納イメージをエクスポートするか設定する。"""
        self._image_export = image_export
        self._force_exportsetting = force

    def get_image_export(self):
        """XML変換時に格納イメージをエクスポートする場合はTrue。
        親要素がある場合、親の設定が優先される。"""
        if self._force_exportsetting:
            return self._image_export

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

        # xmlファイルパス
        if self.xmltype in ("Summary", "Environment"):
            path = util.join_paths(self.get_dir(), self.xmltype + ".xml")
            path = util.check_duplicate(path)
        elif self.xmltype == "Party":
            name = util.check_filename(self.name)
            path = util.join_paths(self.get_dir(), "Party", name)
            path = util.check_duplicate(path)
            path = util.join_paths(path, "Party.xml")
        else:
            name = util.check_filename(self.name) + ".xml"

            # シナリオデータは先頭にidを付与
            if not self.is_yadodata():
                name = str(self.id).zfill(2) + "_" + name

            path = util.join_paths(self.get_dir(), self.xmltype, name)
            path = util.check_duplicate(path)

        # xml出力

        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        data = self.get_data()
        cw.data.CWPyElementTree(element=data).write(path)
        self.xmlpath = path
        return path

    def export_image(self):
        """内部画像を出力する"""
        if not hasattr(self, "image"):
            return ""

        if not self.image:
            return ""

        if not self.get_image_export():
            # パスの代わりにバイナリイメージを使用する
            return cw.binary.image.data_to_code(self.image)

        basedir = self.materialbasedir
        if not basedir:
            basedir = self.get_dir()

        # 画像保存ディレクトリ
        if self.xmltype == "Summary":
            imgdir = basedir
        elif self.xmltype == "BeastCard" and self.summoneffect:
            imgdir = self.get_imgdir()
            if not basedir:
                basedir = self.get_root().materialbasedir

            if not imgdir:
                root = self.get_root()
                name = util.check_filename(root.name)
                mdir = self.get_materialdir()
                if mdir == "":
                    imgdir = util.join_paths(basedir, root.xmltype, name)
                else:
                    imgdir = util.join_paths(basedir, mdir, root.xmltype, name)
                imgdir = util.check_duplicate(imgdir)
                self.set_imgdir(imgdir)

        elif self.xmltype in ("Adventurer", "SkillCard", "ItemCard",
                                                    "BeastCard", "CastCard"):
            name = util.check_filename(self.name)
            mdir = self.get_materialdir()
            if mdir == "":
                imgdir = util.join_paths(basedir, self.xmltype, name)
            else:
                imgdir = util.join_paths(basedir, mdir, self.xmltype, name)
            imgdir = util.check_duplicate(imgdir)
            self.set_imgdir(imgdir)
        else:
            mdir = self.get_materialdir()
            if mdir == "":
                imgdir = util.join_paths(basedir, self.xmltype)
            else:
                imgdir = util.join_paths(basedir, mdir, self.xmltype)

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

        with open(path, "wb") as f:
            f.write(self.image)
            f.flush()
            f.close()

        # 最後に参照パスを返す
        path = path.replace(basedir + "/", "", 1)
        return util.repl_escapechar(path)

    @staticmethod
    def check_imgpath(f, e_imgpath, defpostype):
        """ImagePath要素のWSNバージョンをチェックする。"""
        if e_imgpath is None:
            return
        assert e_imgpath.tag in ("ImagePath", "Talk"), e_imgpath.tag
        postype = e_imgpath.getattr(".", "positiontype", "Default")
        if postype in (defpostype, "Default"):
            return
        f.check_wsnversion("2")

    @staticmethod
    def check_coupon(f, coupon):
        """称号名couponがシステムクーポンであればWSNバージョンをチェックする。
        """
        if coupon in (u"＠効果対象", u"＠効果対象外", u"＠イベント対象", u"＠使用者"):
            f.check_wsnversion("2")

    @staticmethod
    def import_image(f, imagepath, convertbitmap=True, fullpath=False, defpostype="TopLeft"):
        """imagepathの画像を読み込み、バイナリデータとして返す。
        ビットマップ以外であればビットマップに変換する。
        """
        if isinstance(imagepath, cw.data.CWPyElement):
            e = imagepath
            if e.tag == "ImagePath":
                CWBinaryBase.check_imgpath(f, e, defpostype)
                imagepath = e.text
            elif e.tag == "ImagePaths":
                if 1 < len(e):
                    f.check_wsnversion("1")
                CWBinaryBase.check_imgpath(f, e.find("ImagePath"), defpostype)
                imagepath = e.gettext("ImagePath", "")
            else:
                imagepath = ""

        if not imagepath:
            return None

        if cw.binary.image.path_is_code(imagepath):
            image = cw.binary.image.code_to_data(imagepath)
        else:
            if fullpath:
                fpath = imagepath
            else:
                fpath = cw.util.join_paths(cw.cwpy.sdata.tempdir, imagepath)
                if not os.path.isfile(fpath):
                    fpath = cw.util.join_paths(cw.cwpy.tempdir, imagepath)
                    if not os.path.isfile(fpath):
                        fpath = cw.util.join_paths(cw.cwpy.yadodir, imagepath)
                        if not os.path.isfile(fpath):
                            return None

            with open(fpath, "rb") as f:
                image = f.read()
                f.close()

        if convertbitmap and cw.util.get_imageext(image) <> ".bmp":
            with io.BytesIO(image) as f:
                data = wx.ImageFromStream(f)
                f.close()
            with io.BytesIO() as f:
                data.SaveStream(f, wx.BITMAP_TYPE_BMP)
                image = f.getvalue()
                f.close()

        return image

    def get_data(self):
        """CWPyElementのインスタンスを返す。"""
        return None

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

    @staticmethod
    def materialpath(path):
        """素材パスを逆変換する。"""
        if not path:
            return ""

        if path.startswith("Material/"):
            return path[9:]
        else:
            return path

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
        elif n == 66:
            return "Substitute", "Step"       # ステップ代入(1.30)
        elif n == 67:
            return "Substitute", "Flag"       # フラグ代入(1.30)
        elif n == 68:
            return "Branch", "StepValue"      # ステップ比較(1.30)
        elif n == 69:
            return "Branch", "FlagValue"      # フラグ比較(1.30)
        elif n == 70:
            return "Branch", "RandomSelect"   # ランダム選択(1.30)
        elif n == 71:
            return "Branch", "KeyCode"        # キーコード所持分岐(1.50)
        elif n == 72:
            return "Check", "Step"            # ステップ判定(1.50)
        elif n == 73:
            return "Branch", "Round"          # ラウンド分岐(1.50)
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_contenttype(ctype, n):
        if ctype == "Start" and n == "":
            return 0
        elif ctype == "Link" and n == "Start":
            return 1
        elif ctype == "Start" and n == "Battle":
            return 2
        elif ctype == "End" and n == "":
            return 3
        elif ctype == "End" and n == "BadEnd":
            return 4
        elif ctype == "Change" and n == "Area":
            return 5
        elif ctype == "Talk" and n == "Message":
            return 6
        elif ctype == "Play" and n == "Bgm":
            return 7
        elif ctype == "Change" and n == "BgImage":
            return 8
        elif ctype == "Play" and n == "Sound":
            return 9
        elif ctype == "Wait" and n == "":
            return 10
        elif ctype == "Effect" and n == "":
            return 11
        elif ctype == "Branch" and n == "Select":
            return 12
        elif ctype == "Branch" and n == "Ability":
            return 13
        elif ctype == "Branch" and n == "Random":
            return 14
        elif ctype == "Branch" and n == "Flag":
            return 15
        elif ctype == "Set" and n == "Flag":
            return 16
        elif ctype == "Branch" and n == "MultiStep":
            return 17
        elif ctype == "Set" and n == "Step":
            return 18
        elif ctype == "Branch" and n == "Cast":
            return 19
        elif ctype == "Branch" and n == "Item":
            return 20
        elif ctype == "Branch" and n == "Skill":
            return 21
        elif ctype == "Branch" and n == "Info":
            return 22
        elif ctype == "Branch" and n == "Beast":
            return 23
        elif ctype == "Branch" and n == "Money":
            return 24
        elif ctype == "Branch" and n == "Coupon":
            return 25
        elif ctype == "Get" and n == "Cast":
            return 26
        elif ctype == "Get" and n == "Item":
            return 27
        elif ctype == "Get" and n == "Skill":
            return 28
        elif ctype == "Get" and n == "Info":
            return 29
        elif ctype == "Get" and n == "Beast":
            return 30
        elif ctype == "Get" and n == "Money":
            return 31
        elif ctype == "Get" and n == "Coupon":
            return 32
        elif ctype == "Lose" and n == "Cast":
            return 33
        elif ctype == "Lose" and n == "Item":
            return 34
        elif ctype == "Lose" and n == "Skill":
            return 35
        elif ctype == "Lose" and n == "Info":
            return 36
        elif ctype == "Lose" and n == "Beast":
            return 37
        elif ctype == "Lose" and n == "Money":
            return 38
        elif ctype == "Lose" and n == "Coupon":
            return 39
        elif ctype == "Talk" and n == "Dialog":
            return 40
        elif ctype == "Set" and n == "StepUp":
            return 41
        elif ctype == "Set" and n == "StepDown":
            return 42
        elif ctype == "Reverse" and n == "Flag":
            return 43
        elif ctype == "Branch" and n == "Step":
            return 44
        elif ctype == "Elapse" and n == "Time":
            return 45
        elif ctype == "Branch" and n == "Level":
            return 46
        elif ctype == "Branch" and n == "Status":
            return 47
        elif ctype == "Branch" and n == "PartyNumber":
            return 48
        elif ctype == "Show" and n == "Party":
            return 49
        elif ctype == "Hide" and n == "Party":
            return 50
        elif ctype == "Effect" and n == "Break":
            return 51
        elif ctype == "Call" and n == "Start":
            return 52
        elif ctype == "Link" and n == "Package":
            return 53
        elif ctype == "Call" and n == "Package":
            return 54
        elif ctype == "Branch" and n == "Area":
            return 55
        elif ctype == "Branch" and n == "Battle":
            return 56
        elif ctype == "Branch" and n == "CompleteStamp":
            return 57
        elif ctype == "Get" and n == "CompleteStamp":
            return 58
        elif ctype == "Lose" and n == "CompleteStamp":
            return 59
        elif ctype == "Branch" and n == "Gossip":
            return 60
        elif ctype == "Get" and n == "Gossip":
            return 61
        elif ctype == "Lose" and n == "Gossip":
            return 62
        elif ctype == "Branch" and n == "IsBattle":
            return 63
        elif ctype == "Redisplay" and n == "":
            return 64
        elif ctype == "Check" and n == "Flag":
            return 65
        elif ctype == "Substitute" and n == "Step": # 1.30
            return 66
        elif ctype == "Substitute" and n == "Flag": # 1.30
            return 67
        elif ctype == "Branch" and n == "StepValue": # 1.30
            return 68
        elif ctype == "Branch" and n == "FlagValue": # 1.30
            return 69
        elif ctype == "Branch" and n == "RandomSelect": # 1.30
            return 70
        elif ctype == "Branch" and n == "KeyCode": # 1.50
            return 71
        elif ctype == "Check" and n == "Step": # 1.50
            return 72
        elif ctype == "Branch" and n == "Round": # 1.50
            return 73
        else:
            raise ValueError(ctype + ", " + n)

#-------------------------------------------------------------------------------
# 適用メンバ・適用範囲
#-------------------------------------------------------------------------------

    def conv_target_member(self, n):
        """引数の値から、「適用メンバ」の種類を返す。
        0:Selected(現在選択中のメンバ), 1:Random(ランダムメンバ),
        2:Party(現在選択中以外のメンバ)
        睡眠者有効ならば＋3で、返り値の文字列の後ろに"Sleep"を付ける。
        さらに6:Party(パーティの全員。効果コンテントの時に使う)
        """
        if n == 0:
            return "Selected"
        elif n == 1:
            return "Random"
        elif n == 2:
            return "Party"
        elif n == 3:
            return "SelectedSleep"
        elif n == 4:
            return "RandomSleep"
        elif n == 5:
            return "PartySleep"
        elif n == 6: # 存在するか不明だが残しておく
            return "Party"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_target_member(n):
        if n == "Selected":
            return 0
        elif n == "Random":
            return 1
        elif n == "Unselected": # 存在するか不明だが残しておく
            return 2
        elif n == "SelectedSleep":
            return 3
        elif n == "RandomSleep":
            return 4
        elif n == "PartySleep":
            return 5
        elif n == "Party":
            return 2
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_target_member_dialog(self, n):
        """引数の値から、台詞コンテントの話者を返す。
        0:Selected(現在選択中のメンバ), 1:Random(ランダムメンバ),
        2:Unselected(現在選択中以外のメンバ)
        以降は1.50～
        3:Valued(評価メンバ)
        """
        if n in (-1, 0): # 稀に-1になっている事がある
            return "Selected"
        elif n == 1:
            return "Random"
        elif n == 2:
            return "Unselected"
        elif n == 3:
            return "Valued"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_target_member_dialog(n, f):
        if n == "Selected":
            return 0
        elif n == "Random":
            return 1
        elif n == "Unselected":
            return 2
        elif n == "Valued":
            f.check_version(1.50)
            return 3
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_target_scope(n):
        if n == "Selected":
            return 0
        elif n == "Random":
            return 1
        elif n == "Party":
            return 2
        elif n == "Backpack":
            return 3
        elif n == "PartyAndBackpack":
            return 4
        elif n == "Field":
            return 5
        elif n in ("CouponHolder", "CardTarget"):
            f.check_wsnversion("2")
            return 0
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_target_scope_coupon(self, n):
        """引数の値から、「適用範囲」の種類を返す(1.30～のクーポン分岐)。
        0:Selected(現在選択中のメンバ), 1:Random(パーティの誰か一人),
        2:Party(パーティの全員), 3:Field(フィールド全体)
        """
        if n == 0:
            return "Selected"
        elif n == 1:
            return "Random"
        elif n == 2:
            return "Party"
        elif n == 3:
            return "Field"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_target_scope_coupon(n, f):
        if n == "Selected":
            return 0
        elif n == "Random":
            return 1
        elif n == "Party":
            return 2
        elif n == "Field":
            f.check_version(1.30)
            return 3
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_castranges(self, n):
        """引数の値から、「適用メンバ」の種類をsetで返す(1.30)。
        0b0001:パーティ
        0b0010:エネミー
        0b0100:同行NPC
        """
        s = set()
        if (n & 0b0001) <> 0:
            s.add("Party")
        if (n & 0b0010) <> 0:
            s.add("Enemy")
        if (n & 0b0100) <> 0:
            s.add("Npc")
        return s

    @staticmethod
    def unconv_castranges(data):
        value = 0
        for n in data:
            if n.text == "Party":
                value |= 0b0001
            elif n.text == "Enemy":
                value |= 0b0010
            elif n.text == "Npc":
                value |= 0b0100
            else:
                raise cw.binary.cwfile.UnsupportedError()
        return value

    def conv_keycoderange(self, n):
        """引数の値から、「キーコード取得範囲」の種類を返す(1.50～のキーコード所持分岐)。
        0:Selected(現在選択中のメンバ), 1:Random(パーティの誰か一人),
        2:Backpack(荷物袋), 3:PartyAndBackpack(全体(荷物袋含む))
        """
        if n == 0:
            return "Selected"
        elif n == 1:
            return "Random"
        elif n == 2:
            return "Backpack"
        elif n == 3:
            return "PartyAndBackpack"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_keycoderange(n):
        if n == "Selected":
            return 0
        elif n == "Random":
            return 1
        elif n == "Backpack":
            return 2
        elif n == "PartyAndBackpack":
            return 3
        elif n in ("CouponHolder", "CardTarget"):
            f.check_wsnversion("2")
            return 0
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_spreadtype(n):
        if n == "Auto":
            return 0
        elif n == "Custom":
            return 1
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_statustype(self, n):
        """引数の値から、状態を返す。
        0:Active(行動可能), 1:Inactive(行動不可), 2:Alive(生存), 3:Dead(非生存),
        4:Fine(健康), 5:Injured(負傷), 6:Heavy-Injured(重傷),
        7:Unconscious(意識不明), 8:Poison(中毒), 9:Sleep(眠り),
        10:Bind(呪縛), 11:Paralyze(麻痺・石化)
        以降は1.30～
        12:Confuse(混乱), 13:Overheat(激昂), 14:Brave(勇敢), 15:Panic(恐慌)
        以降は1.50～
        16:Silence(沈黙), 17:FaceUp(暴露), 18:AntiMagic(魔法無効化),
        19:UpAction(行動力上昇), 20:UpAvoid(回避力上昇),
        21:UpResist(抵抗力上昇), 22:UpDefense(防御力上昇),
        23:DownAction(行動力低下), 24:DownAvoid(回避力低下),
        25:DownResist(抵抗力低下), 26:DownDefense(防御力低下)
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
        elif n == 12:
            return "Confuse"
        elif n == 13:
            return "Overheat"
        elif n == 14:
            return "Brave"
        elif n == 15:
            return "Panic"
        elif n == 16:
            return "Silence"
        elif n == 17:
            return "FaceUp"
        elif n == 18:
            return "AntiMagic"
        elif n == 19:
            return "UpAction"
        elif n == 20:
            return "UpAvoid"
        elif n == 21:
            return "UpResist"
        elif n == 22:
            return "UpDefense"
        elif n == 23:
            return "DownAction"
        elif n == 24:
            return "DownAvoid"
        elif n == 25:
            return "DownResist"
        elif n == 26:
            return "DownDefense"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_statustype(n, f):
        if n == "Active":
            return 0
        elif n == "Inactive":
            return 1
        elif n == "Alive":
            return 2
        elif n == "Dead":
            return 3
        elif n == "Fine":
            return 4
        elif n == "Injured":
            return 5
        elif n == "HeavyInjured":
            return 6
        elif n == "Unconscious":
            return 7
        elif n == "Poison":
            return 8
        elif n == "Sleep":
            return 9
        elif n == "Bind":
            return 10
        elif n == "Paralyze":
            return 11
        elif n == "Confuse":
            f.check_version(1.30)
            return 12
        elif n == "Overheat":
            f.check_version(1.30)
            return 13
        elif n == "Brave":
            f.check_version(1.30)
            return 14
        elif n == "Panic":
            f.check_version(1.30)
            return 15
        elif n == "Silence":
            f.check_version(1.50)
            return 16
        elif n == "FaceUp":
            f.check_version(1.50)
            return 17
        elif n == "AntiMagic":
            f.check_version(1.50)
            return 18
        elif n == "UpAction":
            f.check_version(1.50)
            return 19
        elif n == "UpAvoid":
            f.check_version(1.50)
            return 20
        elif n == "UpResist":
            f.check_version(1.50)
            return 21
        elif n == "UpDefense":
            f.check_version(1.50)
            return 22
        elif n == "DownAction":
            f.check_version(1.50)
            return 23
        elif n == "DownAvoid":
            f.check_version(1.50)
            return 24
        elif n == "DownResist":
            f.check_version(1.50)
            return 25
        elif n == "DownDefense":
            f.check_version(1.50)
            return 26
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_effectcardtype(self, n):
        """引数の値から、「カード種別」を返す(1.50～のキーコード所持分岐)。
        0:All(全種類), 1:Skill(特殊技能), 2:Item(アイテム), 3:Beast(召喚獣)
        """
        if n == 0:
            return "All"
        elif n == 1:
            return "Skill"
        elif n == 2:
            return "Item"
        elif n == 3:
            return "Beast"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_effectcardtype(n):
        if n == "All":
            return 0
        elif n == "Skill":
            return 1
        elif n == "Item":
            return 2
        elif n == "Beast":
            return 3
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_comparison4(self, n):
        """引数の値から、「4路選択条件」を返す(1.50～のステップ判定)。
        0:=(条件値と一致), 1:<>(条件値と不一致),
        2:<(条件値より大きい), 3:>(条件値より小さい)
        """
        if n == 0:
            return "="
        elif n == 1:
            return "<>"
        elif n == 2:
            return "<"
        elif n == 3:
            return ">"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_comparison4(n):
        if n == "=":
            return 0
        elif n == "<>":
            return 1
        elif n == "<":
            return 2
        elif n == ">":
            return 3
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_comparison3(self, n):
        """引数の値から、「3路選択条件」を返す(1.50～のラウンド判定)。
        0:=(条件値と一致), 1:<(条件値より大きい), 2:>(条件値より小さい)
        """
        if n == 0:
            return "="
        elif n == 1:
            return "<"
        elif n == 2:
            return ">"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_comparison3(n):
        if n == "=":
            return 0
        elif n == "<":
            return 1
        elif n == ">":
            return 2
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_effectmotion_element(n):
        if n == "All":
            return 0
        elif n == "Health":
            return 1
        elif n == "Mind":
            return 2
        elif n == "Miracle":
            return 3
        elif n == "Magic":
            return 4
        elif n == "Fire":
            return 5
        elif n == "Ice":
            return 6
        else:
            raise cw.binary.cwfile.UnsupportedError()

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
            elif n == 8:
                return "CancelAction"            # 行動キャンセル(1.50)
            else:
                raise ValueError(self.fpath)

        elif tabn == 8:
            if n == 0:
                return "SummonBeast"              # 召喚獣召喚
            else:
                raise ValueError(self.fpath)

        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_effectmotion_type(n, f):
        if n == "Heal":
            return 0, 0
        elif n == "Damage":
            return 0, 1
        elif n == "Absorb":
            return 0, 2

        elif n == "Paralyze":
            return 1, 0
        elif n == "DisParalyze":
            return 1, 1
        elif n == "Poison":
            return 1, 2
        elif n == "DisPoison":
            return 1, 3

        elif n == "GetSkillPower":
            return 2, 0
        elif n == "LoseSkillPower":
            return 2, 1

        elif n == "Sleep":
            return 3, 0
        elif n == "Confuse":
            return 3, 1
        elif n == "Overheat":
            return 3, 2
        elif n == "Brave":
            return 3, 3
        elif n == "Panic":
            return 3, 4
        elif n == "Normal":
            return 3, 5

        elif n == "Bind":
            return 4, 0
        elif n == "DisBind":
            return 4, 1
        elif n == "Silence":
            return 4, 2
        elif n == "DisSilence":
            return 4, 3
        elif n == "FaceUp":
            return 4, 4
        elif n == "FaceDown":
            return 4, 5
        elif n == "AntiMagic":
            return 4, 6
        elif n == "DisAntiMagic":
            return 4, 7

        elif n == "EnhanceAction":
            return 5, 0
        elif n == "EnhanceAvoid":
            return 5, 1
        elif n == "EnhanceResist":
            return 5, 2
        elif n == "EnhanceDefense":
            return 5, 3

        elif n == "VanishTarget":
            return 6, 0
        elif n == "VanishCard":
            return 6, 1
        elif n == "VanishBeast":
            return 6, 2

        elif n == "DealAttackCard":
            return 7, 0
        elif n == "DealPowerfulAttackCard":
            return 7, 1
        elif n == "DealCriticalAttackCard":
            return 7, 2
        elif n == "DealFeintCard":
            return 7, 3
        elif n == "DealDefenseCard":
            return 7, 4
        elif n == "DealDistanceCard":
            return 7, 5
        elif n == "DealConfuseCard":
            return 7, 6
        elif n == "DealSkillCard":
            return 7, 7
        elif n == "CancelAction": # 1.50
            f.check_version(1.50)
            return 7, 8

        elif n == "SummonBeast":
            return 8, 0

        elif n == "NoEffect":
            f.check_wsnversion("2")
            return 0, 1

        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_effectmotion_damagetype(n):
        if n == "LevelRatio":
            return 0
        elif n == "Normal":
            return 1
        elif n == "Max":
            return 2
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_card_effecttype(n):
        if n == "Physic":
            return 0
        elif n == "Magic":
            return 1
        elif n == "MagicalPhysic":
            return 2
        elif n == "PhysicalMagic":
            return 3
        elif n == "None":
            return 4
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_card_resisttype(n):
        if n == "Avoid":
            return 0
        elif n == "Resist":
            return 1
        elif n == "Unfail":
            return 2
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_card_visualeffect(n):
        if n == "None":
            return 0
        elif n == "Reverse":
            return 1
        elif n == "Horizontal":
            return 2
        elif n == "Vertical":
            return 3
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_card_physicalability(n):
        if n == "Dex":
            return 0
        elif n == "Agl":
            return 1
        elif n == "Int":
            return 2
        elif n == "Str":
            return 3
        elif n == "Vit":
            return 4
        elif n == "Min":
            return 5
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_card_mentalability(n):
        if n == "Aggressive":
            return 1
        elif n == "Unaggressive":
            return -1
        elif n == "Cheerful":
            return 2
        elif n == "Uncheerful":
            return -2
        elif n == "Brave":
            return 3
        elif n == "Unbrave":
            return -3
        elif n == "Cautious":
            return 4
        elif n == "Uncautious":
            return -4
        elif n == "Trickish":
            return 5
        elif n == "Untrickish":
            return -5
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_card_target(n):
        if n == "None":
            return 0
        elif n == "User":
            return 1
        elif n == "Party":
            return 2
        elif n == "Enemy":
            return 3
        elif n == "Both":
            return 4
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_card_premium(n):
        if n == "Normal":
            return 0
        elif n == "Rare":
            return 1
        elif n == "Premium":
            return 2
        else:
            raise cw.binary.cwfile.UnsupportedError()

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
            return "Sleep"             # 睡眠状態
        elif n == 2:
            return "Confuse"           # 混乱状態
        elif n == 3:
            return "Overheat"          # 激昂状態
        elif n == 4:
            return "Brave"             # 勇敢状態
        elif n == 5:
            return "Panic"             # 恐慌状態
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_mentality(n):
        if n == "Normal":
            return 0
        elif n == "Sleep":
            return 1
        elif n == "Confuse":
            return 2
        elif n == "Overheat":
            return 3
        elif n == "Brave":
            return 4
        elif n == "Panic":
            return 5
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_yadotype(n):
        if n == "Normal":
            return 1
        elif n == "Debug":
            return 2
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_yado_summaryview(n):
        if n == "HideHiddenAndCompleteScenario":
            return 0
        elif n == "HideHiddenScenario":
            return 1
        elif n == "ShowAll":
            return 2
        elif n == "ShowFittingScenario":
            return 3
        else:
            raise cw.binary.cwfile.UnsupportedError()

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

    @staticmethod
    def unconv_yado_bgchange(n):
        if n == "NoAnimation":
            return 0
        elif n == "ReedShape":
            return 1
        elif n == "ColorShade":
            return 2
        elif n == "ReplaceDot":
            return 3
        else:
            raise cw.binary.cwfile.UnsupportedError()

#-------------------------------------------------------------------------------
#　特殊セル関連(1.50～)
#-------------------------------------------------------------------------------

    def conv_borderingtype(self, n):
        """引数の値から、テキストセルの縁取り方式を返す。
        0:縁取り形式1, 1:縁取り形式2
        """
        if n == 0:
            return "Outline"
        elif n == 1:
            return "Inline"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_borderingtype(n):
        if n == "Outline":
            return 0
        elif n == "Inline":
            return 1
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_blendmode(self, n):
        """引数の値から、カラーセルの合成方法を返す。
        0,1:上書き, 2:加算, 3:減算, 4:乗算
        """
        if n in (0, 1):
            return "Normal"
        elif n == 2:
            return "Add"
        elif n == 3:
            return "Subtract"
        elif n == 4:
            return "Multiply"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_blendmode(n):
        if n == "Normal":
            return 0
        elif n == "Add":
            return 2
        elif n == "Subtract":
            return 3
        elif n == "Multiply":
            return 4
        else:
            raise cw.binary.cwfile.UnsupportedError()

    def conv_gradientdir(self, n):
        """引数の値から、グラデーション方向を返す。
        0: グラデーション無し, 1:左から右, 2: 上から下
        """
        if n == 0:
            return "None"
        elif n == 1:
            return "LeftToRight"
        elif n == 2:
            return "TopToBottom"
        else:
            raise ValueError(self.fpath)

    @staticmethod
    def unconv_gradientdir(n):
        if n == "None":
            return 0
        elif n == "LeftToRight":
            return 1
        elif n == "TopToBottom":
            return 2
        else:
            raise cw.binary.cwfile.UnsupportedError()

def main():
    pass

if __name__ == "__main__":
    main()

