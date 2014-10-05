#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re

import cw


def join_paths(*paths):
    """パス結合。"""
    return "/".join(filter(lambda a: a, paths)).replace("\\", "/").strip("/")

def check_filename(name):
    """ファイル名として適切かどうかチェックして返す。
    name: チェックするファイルネーム
    """
    # 空白のみの名前かどうかチェックし、その場合は"noname"を返す
    if re.match(ur"^[\s　]+$", name):
        return "noname"

    # エスケープしていたxmlの制御文字を元に戻し、
    # ファイル名使用不可文字を代替文字に置換
    seq = (("&amp;", "&"),
           ("&lt;", "<"),
           ("&gt;", ">"),
           ("&quot;", '"'),
           ("&apos;", "'"),
           ('\\', u'￥'),
           ('/', u'／'),
           (':', u'：'),
           (',', u'，'),
           (';', u'；'),
           ('*', u'＊'),
           ('?', u'？'),
           ('"', u'”'),
           ('<', u'＜'),
           ('>', u'＞'),
           ('|', u'｜'),
           ('"', u'”'))

    for s, s2 in seq:
        name = name.replace(s, s2)

    # 両端の空白を削除
    name, ext = cw.util.splitext(name)
    return name.strip() + ext.strip()

def check_duplicate(path):
    """パスの重複チェック。
    引数のパスをチェックし、重複していたら、
    ファイル・フォルダ名の後ろに"(n)"を付加して返す。
    path: チェックするパス。
    """
    dpath, basename = os.path.split(path)
    fname, ext = cw.util.splitext(basename)
    count = 2

    while os.path.exists(path):
        basename = "%s(%s)%s" % (fname, str(count), ext)
        path = join_paths(dpath, basename)
        count += 1

    return path

def repl_escapechar(s):
    """xmlの制御文字をエスケープする。
    s: エスケープ処理を行う文字列。
    """
    seq = (("&", "&amp;"),
           ("<", "&lt;"),
           (">", "&gt;"),
           ('"', "&quot;"),
           ("'", "&apos;"))

    for old, new in seq:
        s = s.replace(old, new)

    return s

def repl_specialchar(s):
    """特殊文字"\\[a-zA-Z0-9]"のエスケープ処理を行う。
    s: エスケープ処理を行う文字列。
    """
    def repl_metachar(m):
        return m.group(0).replace("\\", u"￥")

    return re.sub(r"\\[a-zA-Z0-9]", repl_metachar, s)

def main():
    pass

if __name__ == "__main__":
    main()
