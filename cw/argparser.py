#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

class ArgParser(object):
    def __init__(self, appname="", description=""):
        """argparse.ArgumentParserが'-'で始まる
        オプション引数を受け付けないため代替として使用。
        使い方はargparse.ArgumentParserに似ているが細部は異なる。
        appname: ヘルプに表示するアプリケーション名。
        description: アプリケーションの概要。
        """
        self.appname = appname
        self.desc = description
        self.args = {}
        self.largs = []

    def add_argument(self, arg, type, nargs, help, arg2="", default=None):
        """オプションの情報を追加する。
        arg: '-'で始まるオプション名。
        type: オプションの型。str, int, boolのいずれか。
        nargs: オプションが取る引数の数。常に数値で指定する。
        help: オプションの解説。
        arg2: '--'で始まるオプション名。
        default: オプションのデフォルト値。
        """
        argobj = Arg(arg, type, nargs, help, arg2, default)
        self.args[arg] = argobj
        if arg2:
            self.args[arg2] = argobj
        self.largs.append(argobj)

    def parse_args(self, args=None):
        """引数をパースした結果を得る。
        args: 引数のリスト。未指定の場合はsys.argvを使用する。
        """
        if args is None:
            args = sys.argv[1:]
        else:
            args = args[:]
        r = ArgResult()
        keys = self.args.keys()
        try:
            while args:
                arg = args.pop(0)
                if arg in self.args:
                    argobj = self.args[arg]
                    val = argobj.eat(args)
                    setattr(r, argobj.arg[1:], val)
                    keys.remove(arg)
                    if argobj.arg2:
                        setattr(r, argobj.arg2[2:], val)
                        keys.remove(argobj.arg2)
                else:
                    r.leftovers.append(arg)
        except:
            print u"起動引数が正しくありません: %s" % (arg)
            print
            self.print_help()
            return None

        for key in keys:
            argobj = self.args[key]
            setattr(r, argobj.arg[1:], argobj.default)
            if argobj.arg2:
                setattr(r, argobj.arg2[2:], argobj.default)

        return r

    def print_help(self):
        """ヘルプメッセージを表示する。
        """
        s = ["Usage:", self.appname]
        for arg in self.largs:
            help = arg.get_help("|")
            s.append("[%s]" % (help))
        print " ".join(s)
        print
        print self.desc
        print
        print u"オプション:"
        mlen = 0
        for arg in self.largs:
            help = arg.get_help()
            mlen = max(len(help), mlen)
        for arg in self.largs:
            s = arg.get_help()
            s = s.ljust(mlen)
            print "  %s  %s" % (s, ('\n' + ' '*(mlen+4)).join(arg.help.splitlines()))

class ArgResult(object):
    def __init__(self):
        """起動オプションを解析した結果を持つオブジェクト。
        解析対象にならなかったオプションはleftoversメンバに記録される。
        """
        self.leftovers = []

class Arg(object):
    def __init__(self, arg, type, nargs, help, arg2="", default=None):
        """オプション情報。
        arg: '-'で始まるオプション名。
        type: オプションの型。str, int, boolのいずれか。
        nargs: オプションが取る引数の数。常に数値で指定する。
        help: オプションの解説。
        arg2: '--'で始まるオプション名。
        default: オプションのデフォルト値。
        """
        self.arg = arg
        self.arg2 = arg2
        self.type = type
        self.nargs = nargs
        self.help = help
        self.default = default

    def eat(self, args):
        """argsからオプション引数を得る。
        argsの要素は、得られた引数の分だけ
        前方から除去される。
        """
        if self.nargs == 1:
            return self.parse(args.pop(0))
        elif 1 < self.nargs:
            seq = []
            for _i in xrange(len(self.nargs)):
                seq.append(self.parse(args.pop(0)))
            return seq
        else:
            return True

    def parse(self, value):
        """型に応じて引数をパースする。"""
        if self.type == int:
            return int(value)
        elif self.type == str:
            return value

    def get_help(self, sep=", "):
        """ヘルプメッセージ用のテキストを生成する。
        """
        s = self.arg
        if self.arg2:
            s = "%s%s%s" % (s, sep, self.arg2)
        if self.nargs:
            return "%s <%s>" % (s, self.arg[1:].upper())
        else:
            return s

def main():
    parser = ArgParser(appname="args.py", description="Process some integers.")
    parser.add_argument("-h", type=bool, nargs=0,
                       help=u"このメッセージを表示して終了します。", arg2="--help", default=False)
    parser.add_argument("-y", type=str, nargs=1,
                       help="help1\nhelp2", default="bbb")
    parser.add_argument("-dbg", type=str, nargs=0,
                       help="help")

    args = parser.parse_args()
    if not args:
        sys.exit(-1)
    if args.help:
        parser.print_help()
        return
    print "-y  :", args.y
    print "-dbg:", args.dbg
    print "    :", args.leftovers

if __name__ == "__main__":
    main()
