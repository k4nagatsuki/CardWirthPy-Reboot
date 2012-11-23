#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import shutil

import util
import cwfile
import summary
import area
import battle
import cast
import item
import info
import package
import skill
import beast


class CWScenario(object):
    def __init__(self, path, dstdir, skintype, materialdir="Material"):
        """カードワースのシナリオを読み込み、XMLファイルに変換するクラス。
        path: カードワースシナリオフォルダのパス。
        dstdir: 変換先ディレクトリ。
        skintype: スキンタイプ。
        """
        self.name = os.path.basename(path)
        self.path = path
        self.dir = util.join_paths(dstdir, os.path.basename(self.path))
        self.dir = util.check_duplicate(self.dir)
        self.skintype = skintype
        self.materialdir = materialdir
        # progress dialog data
        self.message = ""
        self.curnum = 0
        self.maxnum = 1
        # 読み込んだデータリスト
        self.datalist = []
        # エラーログ
        self.errorlog = ""
        # pathにあるファイル・ディレクトリを
        # (シナリオファイル,素材ファイル,その他ファイル, ディレクトリ)に分ける。
        exts_mat = set(["bmp", "jpg", "jpeg", "wav", "wave", "mid", "midi",
                                                    "jpdc", "jpy1", "jptx"])
        self.cwfiles = []
        self.materials = []
        self.otherfiles = []
        self.otherdirs = []
        self.summarypath = None

        # 格納イメージ。
        # Key=wsmまたはwidファイルのパス, Value=イメージデータ(エリアのみ配列)
        self.imagepool = {}

        for name in os.listdir(self.path):
            path = util.join_paths(self.path, name)

            if os.path.isfile(path):
                ext = os.path.splitext(name)[1].lstrip(".").lower()

                if name == "Summary.wsm" and not self.summarypath:
                    self.summarypath = path
                    self.cwfiles.append(path)
                elif ext == "wid":
                    self.cwfiles.append(path)
                elif ext in exts_mat:
                    self.materials.append(path)
                else:
                    self.otherfiles.append(path)

            else:
                self.otherdirs.append(path)

    def is_convertible(self):
        if not self.summarypath:
            return False

        try:
            data = self.load_file(self.summarypath)
        except:
            return False

        if data.version >= 4:
            return True
        else:
            return False

    def write_errorlog(self, s):
        self.errorlog += s + "\n"

    def load(self):
        """シナリオファイルのリストを読み込む。
        種類はtypeで判別できる(見出しは"-1"、パッケージは"7"となっている)。
        """
        self.datalist = []

        for path in self.cwfiles:
            try:
                data = self.load_file(path)
                self.datalist.append(data)
            except:
                s = os.path.basename(path)
                s = u"%s は読込できませんでした。\n" % (s)
                self.write_errorlog(s)

        self.maxnum = len(self.datalist)
        self.maxnum += len(self.materials)
        self.maxnum += len(self.otherfiles)
        self.maxnum += len(self.otherdirs)

    def load_file(self, path, nameonly=False):
        """引数のファイル(wid, wsmファイル)を読み込む。"""
        f = cwfile.CWFile(path, "rb")

        if path == self.summarypath:
            data = summary.Summary(None, f, nameonly=nameonly)
            data.skintype = self.skintype
            self.imagepool[path] = data.image
        else:
            filetype = f.byte()
            f.seek(0)

            if filetype == 0:
                data = area.Area(None, f, nameonly=nameonly)
                mimages = []
                if not nameonly:
                    for mcard in data.mcards:
                        mimages.append(mcard.image)
                self.imagepool[path] = mimages
            elif filetype == 1:
                data = battle.Battle(None, f, nameonly=nameonly)
            elif filetype == 2:
                data = cast.CastCard(None, f, nameonly=nameonly)
                self.imagepool[path] = data.image
            elif filetype == 3:
                data = item.ItemCard(None, f, nameonly=nameonly)
                self.imagepool[path] = data.image
            elif filetype == 4:
                if "Package" in os.path.basename(path):
                    data = package.Package(None, f, nameonly=nameonly)
                else:
                    data = info.InfoCard(None, f, nameonly=nameonly)
                    self.imagepool[path] = data.image

            elif filetype == 5:
                data = skill.SkillCard(None, f, nameonly=nameonly)
                self.imagepool[path] = data.image
            elif filetype == 6:
                data = beast.BeastCard(None, f, nameonly=nameonly)
                self.imagepool[path] = data.image
            else:
                f.close()
                raise ValueError(path)

        f.close()
        data.set_materialdir(self.materialdir)
        return data

    def convert(self):
        if not self.datalist:
            self.load()

        self.curnum = 0

        # シナリオファイルをxmlに変換
        for data in self.datalist:
            self.message = u"%s を変換中" % (os.path.basename(data.fpath))
            self.curnum += 1

            try:
                data.create_xml(self.dir)
            except:
                s = os.path.basename(data.fpath)
                s = u"%s は変換できませんでした。\n" % (s)
                self.write_errorlog(s)

        # 素材ファイルをMaterialディレクトリにコピー
        materialdir = util.join_paths(self.dir, "Material")

        if not os.path.isdir(materialdir):
            os.makedirs(materialdir)

        for path in self.materials:
            self.message = u"%s をコピー中" % (os.path.basename(path))
            self.curnum += 1
            dst = util.join_paths(materialdir, os.path.basename(path))
            dst = util.check_duplicate(dst)
            shutil.copy2(path, dst)

        # その他のファイルをシナリオディレクトリにコピー
        for path in self.otherfiles:
            self.message = u"%s をコピー中" % (os.path.basename(path))
            self.curnum += 1
            dst = util.join_paths(self.dir, os.path.basename(path))
            dst = util.check_duplicate(dst)
            shutil.copy2(path, dst)

        # ディレクトリをシナリオディレクトリにコピー
        for path in self.otherdirs:
            self.message = u"%s をコピー中" % (os.path.basename(path))
            self.curnum += 1
            dst = util.join_paths(self.dir, os.path.basename(path))
            dst = util.check_duplicate(dst)
            shutil.copytree(path, dst)

        self.curnum = self.maxnum
        return self.dir

def main():
    pass

if __name__ == "__main__":
    main()
