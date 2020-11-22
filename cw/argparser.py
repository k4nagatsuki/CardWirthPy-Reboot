#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys

import typing
from typing import Dict, List, Optional, Type, Union


class ArgParser(object):
    def __init__(self, appname: str = "", description: str = "") -> None:
        """argparse.ArgumentParserが'-'で始まる
        オプション引数を受け付けないため代替として使用。
        使い方はargparse.ArgumentParserに似ているが細部は異なる。
        appname: ヘルプに表示するアプリケーション名。
        description: アプリケーションの概要。
        """
        self.appname = appname
        self.desc = description
        self.args: Dict[str, Arg] = {}
        self.largs: List[Arg] = []

    def add_argument(self, arg: str, argtype: Union[Type[bool], Type[str]], nargs: int, helptext: str, arg2: str = "",
                     default: Optional[Union[str, int, bool]] = None, metavar: Optional[str] = None) -> None:
        """オプションの情報を追加する。
        arg: '-'で始まるオプション名。
        argtype: オプションの型。str, int, boolのいずれか。
        nargs: オプションが取る引数の数。常に数値で指定する。
        helptext: オプションの解説。
        arg2: '--'で始まるオプション名。
        default: オプションのデフォルト値。
        metavar: ヘルプで表示される引数値。
        """
        argobj = Arg(arg, argtype, nargs, helptext, arg2, default, metavar)
        self.args[arg] = argobj
        if arg2:
            self.args[arg2] = argobj
        self.largs.append(argobj)

    def parse_args(self, args: Optional[List[str]] = None) -> Optional["ArgResult"]:
        """引数をパースした結果を得る。
        args: 引数のリスト。未指定の場合はsys.argvを使用する。
        """
        if args is None:
            args = sys.argv[1:]
        else:
            args = args[:]
        r = ArgResult()
        keys = list(self.args.keys())
        try:
            while args:
                arg = args.pop(0)
                if arg in self.args:
                    argobj = self.args[arg]
                    val = argobj.eat(args)
                    if argobj.arg:
                        setattr(r, argobj.arg.lstrip("-").replace("-", "_"), val)
                        keys.remove(argobj.arg)
                    if argobj.arg2:
                        setattr(r, argobj.arg2.lstrip("-").replace("-", "_"), val)
                        keys.remove(argobj.arg2)
                else:
                    r.leftovers.append(arg)
        except Exception:
            sys.stderr.write("起動引数が正しくありません: %s\n" % (arg))
            print()
            self.print_help()
            return None

        for key in keys:
            argobj = self.args[key]
            if argobj.arg:
                setattr(r, argobj.arg.lstrip("-").replace("-", "_"), argobj.default)
            if argobj.arg2:
                setattr(r, argobj.arg2.lstrip("-").replace("-", "_"), argobj.default)

        return r

    def print_help(self) -> None:
        """ヘルプメッセージを表示する。
        """
        seq = ["Usage:", self.appname]
        for arg in self.largs:
            helptext = arg.get_help("|")
            seq.append("[%s]" % (helptext))
        print(" ".join(seq))
        print()
        print(self.desc)
        print()
        print("オプション:")
        mlen = 0
        for arg in self.largs:
            helptext = arg.get_help()
            mlen = max(len(helptext), mlen)
        for arg in self.largs:
            s = arg.get_help()
            s = s.ljust(mlen)
            print("  %s  %s" % (s, ('\n' + ' '*(mlen+4)).join(arg.help.splitlines())))


class ArgResult(object):
    def __init__(self) -> None:
        """起動オプションを解析した結果を持つオブジェクト。
        解析対象にならなかったオプションはleftoversメンバに記録される。
        """
        self.leftovers: List[str] = []
        self._int_values: Dict[str, int] = {}
        self._str_values: Dict[str, str] = {}
        self._bool_values: Dict[str, bool] = {}

    def getint(self, key: str) -> int:
        return self._int_values.get(key, 0)

    def setint(self, key: str, value: int) -> None:
        self._int_values[key] = value

    def getstr(self, key: str) -> str:
        return self._str_values.get(key, "")

    def setstr(self, key: str, value: str) -> None:
        self._str_values[key] = value

    def getbool(self, key: str) -> bool:
        return self._bool_values.get(key, False)

    def setbool(self, key: str, value: bool) -> None:
        self._bool_values[key] = value


class Arg(object):
    def __init__(self, arg: str, argtype: Union[Type[bool], Type[str]], nargs: int, helptext: str, arg2: str = "",
                 default: Optional[Union[str, int, bool]] = None, metavar: Optional[str] = None) -> None:
        """オプション情報。
        arg: '-'で始まるオプション名。
        argtype: オプションの型。str, int, boolのいずれか。
        nargs: オプションが取る引数の数。常に数値で指定する。
        helptext: オプションの解説。
        arg2: '--'で始まるオプション名。
        default: オプションのデフォルト値。
        metavar: ヘルプで表示される引数値。
        """
        self.arg = arg
        self.arg2 = arg2
        self.type = argtype
        self.nargs = nargs
        self.help = helptext
        self.default = default
        self.metavar = metavar

    def eat(self, args: List[str]) -> Union[str, int, List[Union[str, int]], bool]:
        """argsからオプション引数を得る。
        argsの要素は、得られた引数の分だけ
        前方から除去される。
        """
        if self.nargs == 1:
            return self.parse(args.pop(0))
        elif 1 < self.nargs:
            seq = []
            for _i in range(self.nargs):
                seq.append(self.parse(args.pop(0)))
            return seq
        else:
            return True

    def parse(self, value: str) -> Union[str, int]:
        """型に応じて引数をパースする。"""
        if self.type == int:
            return int(value)
        elif self.type == str:
            return value
        else:
            assert False

    def get_help(self, sep: str = ", ") -> str:
        """ヘルプメッセージ用のテキストを生成する。
        """
        s = self.arg
        if self.arg2:
            s = "%s%s%s" % (s, sep, self.arg2)
        if self.nargs:
            if self.metavar:
                metavar = self.metavar
            else:
                metavar = self.arg[1:].upper()
            return "%s <%s>" % (s, metavar)
        else:
            return s


def main() -> None:
    parser = ArgParser(appname="args.py", description="Process some integers.")
    parser.add_argument("-h", argtype=bool, nargs=0,
                        helptext="このメッセージを表示して終了します。", arg2="--help", default=False)
    parser.add_argument("-y", argtype=str, nargs=1,
                        helptext="help1\nhelp2", default="bbb")
    parser.add_argument("-dbg", argtype=str, nargs=0,
                        helptext="help")

    args = parser.parse_args()
    if not args:
        sys.exit(-1)
    if args.getbool("help"):
        parser.print_help()
        return
    print("-y  :", args.getstr("y"))
    print("-dbg:", args.getstr("dbg"))
    print("    :", args.leftovers)


if __name__ == "__main__":
    main()
