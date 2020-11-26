#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import decimal
import fnmatch

import cw

from typing import Callable, List, Optional, Tuple, Union


class ComputeException(Exception):
    """式の中で発生する何らかのエラー。"""
    def __init__(self, msg: str, line: int, pos: int) -> None:
        Exception.__init__(self, msg + " Line: %s, Pos: %s" % (line, pos))
        self.line = line
        self.pos = pos


class TokanizeException(ComputeException):
    """字句解析エラー。"""
    def __init__(self, msg: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)


class SemanticsException(ComputeException):
    """構文解析エラー。"""
    def __init__(self, msg: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)


class ZeroDivisionException(ComputeException):
    """ゼロで割ろうとした。"""
    def __init__(self, msg: str, line: int, pos: int) -> None:
        Exception.__init__(self, msg + " Line: %s, Pos: %s" % (line, pos))
        self.line = line
        self.pos = pos


class FunctionIsNotDefinedException(ComputeException):
    """関数未定義エラー。"""
    def __init__(self, msg: str, func_name: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name


class ArgumentIsNotDecimalException(ComputeException):
    """関数の引数が数値でない。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: Union[str, decimal.Decimal, bool],
                 line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class ArgumentIsNotStringException(ComputeException):
    """関数の引数が文字列でない。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: Union[str, decimal.Decimal, bool],
                 line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class ArgumentIsNotBooleanException(ComputeException):
    """関数の引数が真偽値でない。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: Union[str, decimal.Decimal, bool],
                 line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class ArgumentsCountException(ComputeException):
    """関数の引数の数が誤っている。"""
    def __init__(self, msg: str, func_name: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name


class InvalidArgumentException(ComputeException):
    """関数の引数が誤っている。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class VariantNotFoundException(ComputeException):
    """汎用変数が存在しない。"""
    def __init__(self, msg: str, path: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.path = path


class FlagNotFoundException(ComputeException):
    """フラグが存在しない。"""
    def __init__(self, msg: str, path: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.path = path


class StepNotFoundException(ComputeException):
    """ステップが存在しない。"""
    def __init__(self, msg: str, path: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.path = path


class InvalidStepValueException(ComputeException):
    """ステップ値が範囲外。"""
    def __init__(self, msg: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)


class DifferentScenarioException(ComputeException):
    """外部シナリオで状態変数を読もうとした。"""
    def __init__(self, msg: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)


class Function(object):
    """関数の名前と引数を保持し、計算を行う。"""
    def __init__(self, name: str, line: int, pos: int,
                 args: List[List[Union["ValueType", "Function", "UnaryOperator", "Operator"]]]) -> None:
        self.name = name.lower()
        self.line = line
        self.pos = pos
        self.args = args

    def call(self, is_differentscenario: bool) -> "ValueType":
        args = []
        for arg in self.args:
            class F(object):
                def __init__(self, arg: List[Union[ValueType, Function, UnaryOperator, Operator]],
                             is_differentscenario: bool) -> None:
                    self.arg = arg
                    self.is_differentscenario = is_differentscenario

                def eval_arg(self) -> ValueType:
                    return calculate(self.arg, self.is_differentscenario)

            args.append(F(arg, is_differentscenario).eval_arg)
        name = self.name
        if name in _functions:
            return _functions[name](args, is_differentscenario, self.line, self.pos)
        else:
            raise FunctionIsNotDefinedException("Function \"%s\" is not defined." % name, name, self.line, self.pos)

    def __repr__(self) -> str:
        return "%s(%s)" % (self.name, ", ".join([str(a) for a in self.args]))


class UnaryOperator(object):
    """単項演算子の保持と実行を行う。"""
    def __init__(self, operator: str, line: int, pos: int) -> None:
        self.operator = operator
        self.line = line
        self.pos = pos

    def call(self, rhs: "ValueType") -> "ValueType":
        o = self.operator
        if o == '+':
            if not isinstance(rhs, DecimalValue):
                raise SemanticsException("value [%s] is not number." % rhs.value, rhs.line, rhs.pos)
            return DecimalValue(rhs.value, self.line, self.pos)
        elif o == '-':
            if not isinstance(rhs, DecimalValue):
                raise SemanticsException("value [%s] is not number." % rhs.value, rhs.line, rhs.pos)
            return DecimalValue(-rhs.value, self.line, self.pos)
        elif o.lower() == "not":
            if not isinstance(rhs, BooleanValue):
                raise SemanticsException("value [%s] is not boolean." % rhs.value, rhs.line, rhs.pos)
            return BooleanValue(not rhs.value, self.line, self.pos)
        else:
            raise SemanticsException("Invalid operator: %s" % o, self.line, self.pos)

    def __repr__(self) -> str:
        return "UOp(%s, %s:%s)" % (self.operator, self.line, self.pos)


class Operator(object):
    """二項演算子の保持と実行を行う。"""
    def __init__(self, operator: str, line: int, pos: int) -> None:
        self.operator = operator
        self.line = line
        self.pos = pos

    def call(self, lhs: "ValueType", rhs: "ValueType") -> "ValueType":
        o = self.operator

        def chk_num() -> Tuple[decimal.Decimal, decimal.Decimal]:
            if not isinstance(lhs, DecimalValue):
                raise SemanticsException("lhs [%s] is not number." % lhs.value, lhs.line, lhs.pos)
            if not isinstance(rhs, DecimalValue):
                raise SemanticsException("rhs [%s] is not number." % rhs.value, rhs.line, rhs.pos)
            assert isinstance(lhs.value, decimal.Decimal)
            assert isinstance(rhs.value, decimal.Decimal)
            return lhs.value, rhs.value

        def chk_bool() -> Tuple[bool, bool]:
            if not isinstance(lhs, BooleanValue):
                raise SemanticsException("lhs [%s] is not boolean." % lhs.value, lhs.line, lhs.pos)
            if not isinstance(rhs, BooleanValue):
                raise SemanticsException("rhs [%s] is not boolean." % rhs.value, rhs.line, rhs.pos)
            assert isinstance(lhs.value, bool)
            assert isinstance(rhs.value, bool)
            return lhs.value, rhs.value
        if o == '+':
            lhs_int, rhs_int = chk_num()
            return DecimalValue(lhs_int + rhs_int, self.line, self.pos)
        elif o == '-':
            lhs_int, rhs_int = chk_num()
            return DecimalValue(lhs_int - rhs_int, self.line, self.pos)
        elif o == '*':
            lhs_int, rhs_int = chk_num()
            return DecimalValue(lhs_int * rhs_int, self.line, self.pos)
        elif o == '/':
            lhs_int, rhs_int = chk_num()
            if rhs.value == 0:
                raise ZeroDivisionException("Division by zero.", self.line, self.pos)
            return DecimalValue(lhs_int / rhs_int, self.line, self.pos)
        elif o == '%':
            lhs_int, rhs_int = chk_num()
            if rhs.value == 0:
                raise ZeroDivisionException("Division by zero.", self.line, self.pos)
            return DecimalValue(lhs_int % rhs_int, self.line, self.pos)
        elif o == '~':
            return StringValue(lhs.to_str() + rhs.to_str(), self.line, self.pos)
        elif o == "<=":
            lhs_int, rhs_int = chk_num()
            return BooleanValue(lhs_int <= rhs_int, self.line, self.pos)
        elif o == ">=":
            lhs_int, rhs_int = chk_num()
            return BooleanValue(lhs_int >= rhs_int, self.line, self.pos)
        elif o == "<":
            lhs_int, rhs_int = chk_num()
            return BooleanValue(lhs_int < rhs_int, self.line, self.pos)
        elif o == ">":
            lhs_int, rhs_int = chk_num()
            return BooleanValue(lhs_int > rhs_int, self.line, self.pos)
        elif o in ("=", "<>"):
            if isinstance(lhs, StringValue) or isinstance(rhs, StringValue):
                r = lhs.to_str() == rhs.to_str()
            elif isinstance(lhs, BooleanValue) or isinstance(rhs, BooleanValue):
                lhs_bool, rhs_bool = chk_bool()
                r = lhs_bool == rhs_bool
            else:
                lhs_int, rhs_int = chk_num()
                r = lhs_int == rhs_int
            if o == "<>":
                r = not r
            return BooleanValue(r, self.line, self.pos)
        elif o.lower() == "and":
            lhs_bool, rhs_bool = chk_bool()
            return BooleanValue(lhs_bool and rhs_bool, self.line, self.pos)
        elif o.lower() == "or":
            lhs_bool, rhs_bool = chk_bool()
            return BooleanValue(lhs_bool or rhs_bool, self.line, self.pos)
        else:
            raise SemanticsException("Invalid operator: %s" % o, self.line, self.pos)

    def __repr__(self) -> str:
        return "Op(%s, %s:%s)" % (self.operator, self.line, self.pos)


class Token(object):
    """行+行内位置を伴うトークン情報。"""
    def __init__(self, token: str, line: int, pos: int) -> None:
        self.token = token
        self.line = line
        self.pos = pos

    def __repr__(self) -> str:
        return "Token(%s, %s:%s)" % (self.token, self.line, self.pos)


class ValueType(object):
    value: Union[str, decimal.Decimal, bool]
    line: int
    pos: int

    def to_str(self) -> str:
        return ""


class DecimalValue(ValueType):
    """数値トークン。"""
    value: decimal.Decimal

    def __init__(self, s: Union[str, decimal.Decimal, int], line: int, pos: int) -> None:
        self.value = decimal.Decimal(s)
        self.line = line
        self.pos = pos

    def to_str(self) -> str:
        s = ("%.8f" % self.value).rstrip("0").rstrip(".")
        if s == "":
            s = "0"
        return s

    def __repr__(self) -> str:
        return "Decimal(%s)" % self.value


class StringValue(ValueType):
    """文字列トークン。"""
    value: str

    def __init__(self, s: str, line: int, pos: int) -> None:
        self.value = s
        self.line = line
        self.pos = pos

    def to_str(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return "String(\"%s\")" % self.value


class BooleanValue(ValueType):
    """真偽値トークン。"""
    value: bool

    def __init__(self, s: bool, line: int, pos: int) -> None:
        self.value = s
        self.line = line
        self.pos = pos

    def to_str(self) -> str:
        return "TRUE" if self.value else "FALSE"

    def __repr__(self) -> str:
        return "Boolean(\"%s\")" % self.value


def parse(s: str) -> List[Union[ValueType, Function, UnaryOperator, Operator]]:
    """文字列sを式として解析し、スタックを生成する。"""
    tokens = []
    bpos = 0
    bm: Optional[re.Match[str]] = None
    line = 1
    pos = 1
    reg = "[0-9]+(\\.[0-9]+)?|[a-z_][a-z_0-9]*|[\\+\\-\\*\\/\\%\\~]|[\\(\\)]|,|@?\"([^\"]|\"\")*\"|or|and|"\
          "<=|>=|<>|<|>|=|true|false|\\n|\\s+"
    for m in re.finditer(reg, s, re.I):
        if bpos is None or m.start() != bpos:
            assert bm is not None
            raise TokanizeException("Invalid Character: %s" % s[bm.end():m.start()], line, pos)
        bpos = m.end()
        t = m.group()
        ln = cw.util.get_strlen(t)
        if not t.isspace():
            tokens.append(Token(t, line, pos))
        bm = m
        if t == "\n":
            line += 1
            pos = 1
        else:
            pos += ln

    def parse_arguments(tokens: List[Token],
                        i: int) -> Tuple[int, List[List[Union[ValueType, Function, UnaryOperator, Operator]]]]:
        if len(tokens) <= i + 1:
            raise SemanticsException("Invalid function call.", tokens[i].line, tokens[i].pos)
        i += 1
        t = tokens[i].token
        if t not in ('('):
            raise SemanticsException("Need an open parenthesis here.", tokens[i].line, tokens[i].pos)
        args = []
        while i + 1 < len(tokens) and tokens[i].token != ')':
            t2 = tokens[i+1]
            if t2.token == ')':
                i += 1
                break
            i, arg = parse_semantics(tokens, i + 1)
            if len(arg):
                args.append(arg)
            else:
                raise SemanticsException("No argument.", t2.line, t2.pos)
        return i + 1, args

    def parse_semantics(tokens: List[Token],
                        i: int) -> Tuple[int, List[Union[ValueType, Function, UnaryOperator, Operator]]]:
        num: List[Union[ValueType, Function, UnaryOperator, Operator]] = []
        op: List[Tuple[int, int, bool, Token]] = []

        isop = True
        parlevel = 0

        while i < len(tokens):
            t = tokens[i].token
            line = tokens[i].line
            pos = tokens[i].pos
            unary = False
            if t.lower() == "not":
                if not isop:
                    raise SemanticsException("Need a boolean here.", line, pos)
                # 真偽値反転演算子
                oplevel = 2
                unary = True
            elif t in ('-', '+'):
                if isop:
                    # 単項演算子
                    oplevel = 99
                    unary = True
                else:
                    # 優先度の低い演算子
                    oplevel = 4
            elif t in ('~'):
                if isop:
                    raise SemanticsException("Need a symbol or number here.", line, pos)
                # 連結子
                oplevel = 4
            elif t in ('/', '*', '%'):
                if isop:
                    raise SemanticsException("Need a symbol or number here.", line, pos)
                # 優先の高い演算子
                oplevel = 5
            elif t in ("<=", ">=", "<>", "<", ">", "="):
                if isop:
                    raise SemanticsException("Need a symbol or number here.", line, pos)
                # 比較演算子
                oplevel = 3
            elif t.lower() == "and":
                if isop:
                    raise SemanticsException("Need a symbol or number here.", line, pos)
                # AND演算子
                oplevel = 1
            elif t.lower() == "or":
                if isop:
                    raise SemanticsException("Need a symbol or number here.", line, pos)
                # OR演算子
                oplevel = 0
            elif t in ('('):
                if not isop:
                    raise SemanticsException("Need an operator here.", line, pos)
                # 開き括弧
                parlevel += 1
                i += 1
                continue
            elif t in (')'):
                if isop:
                    raise SemanticsException("Need a symbol or number here.", line, pos)
                # 閉じ括弧
                if parlevel <= 0:
                    break
                else:
                    parlevel -= 1
                    i += 1
                    continue
            elif t[0] in (','):
                # カンマ区切り
                if parlevel <= 0:
                    break
                elif isop:
                    raise SemanticsException("Need a symbol or number here.", line, pos)
                else:
                    raise SemanticsException("Need an operator here.", line, pos)
            elif '0' <= t[0] <= '9':
                if not isop:
                    raise SemanticsException("Need an operator here.", line, pos)
                # 数値
                num.append(DecimalValue(t, line, pos))
                isop = False
                i += 1
                continue
            elif t[0] in ('"'):
                if not isop:
                    raise SemanticsException("Need an operator here.", line, pos)
                # 文字列
                assert t[-1] == '"'
                num.append(StringValue(t[1:-1].replace('""', '"'), line, pos))
                isop = False
                i += 1
                continue
            elif t[0] in ('@'):
                if not isop:
                    raise SemanticsException("Need an operator here.", line, pos)
                # 汎用変数
                assert t[1] == '"'
                assert t[-1] == '"'
                num.append(Function("var", line, pos, [[StringValue(t[2:-1].replace('""', '"'), line, pos)]]))
                isop = False
                i += 1
                continue
            elif t.lower() in ("true", "false"):
                if not isop:
                    raise SemanticsException("Need an operator here.", line, pos)
                # 真偽値
                num.append(BooleanValue(t.lower() == "true", line, pos))
                isop = False
                i += 1
                continue
            else:
                if not isop:
                    raise SemanticsException("Need an operator here.", line, pos)
                # その他シンボル
                # 現在は関数呼び出しのみ
                i, args = parse_arguments(tokens, i)
                num.append(Function(t, line, pos, args))
                isop = False
                continue

            opval = (parlevel, oplevel, unary, tokens[i])
            while len(op) and opval[:2] <= op[-1][:2]:
                if unary and op[-1][2]:
                    break
                tpl = op.pop()
                t2 = tpl[3]
                if tpl[2]:
                    num.append(UnaryOperator(t2.token, t2.line, t2.pos))
                else:
                    num.append(Operator(t2.token, t2.line, t2.pos))
            op.append(opval)
            isop = True

            i += 1

        while len(op):
            tpl = op.pop()
            t2 = tpl[3]
            if tpl[2]:
                num.append(UnaryOperator(t2.token, t2.line, t2.pos))
            else:
                num.append(Operator(t2.token, t2.line, t2.pos))

        return i, num

    i, num = parse_semantics(tokens, 0)
    if i != len(tokens):
        raise SemanticsException("Invalid semantics.", line, pos)
    return num


def calculate(st: List[Union[ValueType, Function, UnaryOperator, Operator]],
              is_differentscenario: bool = False) -> ValueType:
    """スタックstの式を実行する。"""
    op: List[ValueType] = []
    for t in st:
        if isinstance(t, Function):
            # 関数呼び出し
            v = t.call(is_differentscenario)
        elif isinstance(t, UnaryOperator):
            # 単項演算子
            if not op:
                raise SemanticsException("Invalid semantics.", t.line, t.pos)
            rhs = op.pop()
            v = t.call(rhs)
        elif isinstance(t, Operator):
            # 二項演算子
            if not op:
                raise SemanticsException("Invalid semantics.", t.line, t.pos)
            rhs = op.pop()
            if not op:
                raise SemanticsException("Invalid semantics.", t.line, t.pos)
            lhs = op.pop()
            v = t.call(lhs, rhs)
        else:
            # 数値・文字列・真偽値
            v = t
        op.append(v)
    if not op:
        raise SemanticsException("Invalid semantics.", 0, 0)
    return op.pop(-1)


def eval_expr(st: List[Union[ValueType, Function, UnaryOperator, Operator]],
              is_differentscenario: bool) -> cw.data.Variant:
    return cw.data.Variant(None, None, calculate(st, is_differentscenario).value, "", "")


def _chk_diffsc(is_differentscenario: bool, line: int, pos: int) -> None:
    if is_differentscenario:
        raise DifferentScenarioException("Read a variable at different scenario.", line, pos)


def _chk_argscount(args: List[Callable[[], ValueType]], n: int, func_name: str, line: int, pos: int) -> None:
    if len(args) != n:
        raise ArgumentsCountException("Invalid arguments count: %s != %s" % (n, len(args)), func_name, line, pos)


def _chk_argscount2(args: List[Callable[[], ValueType]], n1: int, n2: int, func_name: str, line: int, pos: int) -> None:
    if not len(args) in (n1, n2):
        raise ArgumentsCountException("Invalid arguments count: %s-%s != %s" % (n1, n2, len(args)), func_name, line,
                                      pos)


def _chk_decimal(arg: ValueType, func_name: str, arg_index: int) -> decimal.Decimal:
    """argがDecimalValueか調べる。"""
    if isinstance(arg, DecimalValue):
        assert isinstance(arg.value, decimal.Decimal)
        return arg.value
    else:
        raise ArgumentIsNotDecimalException("%s is not Decimal." % arg.value, func_name, arg_index, arg.to_str(),
                                            arg.line, arg.pos)


def _chk_minvalue(arg: ValueType, func_name: str, arg_index: int, minvalue: int = 0) -> decimal.Decimal:
    """argが0以上のDecimalValueか調べる。"""
    r = _chk_decimal(arg, func_name, arg_index)
    if r < minvalue:
        raise InvalidArgumentException("%s < %s." % (r, minvalue), func_name, arg_index, arg.to_str(),
                                       arg.line, arg.pos)
    else:
        return r


def _chk_string(arg: ValueType, func_name: str, arg_index: int) -> str:
    """argがStringValueか調べる。"""
    if isinstance(arg, StringValue):
        assert isinstance(arg.value, str)
        return arg.value
    else:
        raise ArgumentIsNotStringException("%s is not String." % arg.value, func_name, arg_index, arg.value,
                                           arg.line, arg.pos)


def _chk_boolean(arg: ValueType, func_name: str, arg_index: int) -> bool:
    """argがBooleanValueか調べる。"""
    if isinstance(arg, BooleanValue):
        assert isinstance(arg.value, bool)
        return arg.value
    else:
        raise ArgumentIsNotBooleanException("%s is not Boolean." % arg.value, func_name, arg_index, arg.value,
                                            arg.line, arg.pos)


def _is_alldecimal(args: List[ValueType], func_name: str) -> bool:
    """argsが全てDecimalValueで構成されているか検査する。"""
    for i, arg in enumerate(args):
        _chk_decimal(arg, func_name, i)
    return True


def _all_eval(args: List[Callable[[], ValueType]]) -> List[ValueType]:
    return [arg() for arg in args]


def _func_max(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> DecimalValue:
    """引数中の最大の値を返す。"""
    args_r = _all_eval(args)
    if len(args_r) and _is_alldecimal(args_r, "MAX"):
        return DecimalValue(max(*map(lambda a: a.value, args_r)) if 1 < len(args_r) else args_r[0].value, line, pos)
    raise ArgumentsCountException("No argments of max.", "MAX", line, pos)


def _func_min(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> DecimalValue:
    """引数中の最小の値を返す。"""
    args_r = _all_eval(args)
    if len(args_r) and _is_alldecimal(args_r, "MIN"):
        return DecimalValue(min(*map(lambda a: a.value, args_r)) if 1 < len(args_r) else args_r[0].value, line, pos)
    raise ArgumentsCountException("No argments of min.", "MIN", line, pos)


def _func_len(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> DecimalValue:
    """文字列の文字数を返す。"""
    _chk_argscount(args, 1, "LEN", line, pos)
    args_r = _all_eval(args)
    a = args_r[0]
    return DecimalValue(len(_chk_string(a, "LEN", 0)), line, pos)


def _func_find(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> DecimalValue:
    """文字列内を検索する。"""
    _chk_argscount2(args, 2, 3, "FIND", line, pos)
    args_r = _all_eval(args)
    a = _chk_string(args_r[0], "FIND", 0)
    t = _chk_string(args_r[1], "FIND", 1)
    if 2 < len(args_r):
        n = args_r[2]
        start = int(_chk_minvalue(n, "FIND", 2))
        if start == 0:
            return DecimalValue(0, line, pos)
        start -= 1
        if len(t) <= start:
            return DecimalValue(0, line, pos)
    else:
        start = 0
    if a == "" and t == "":
        return DecimalValue(0, line, pos)
    r = t[start:].find(a)
    if r == -1:
        return DecimalValue(0, line, pos)
    r += start
    return DecimalValue(r + 1, line, pos)


def _func_left(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> StringValue:
    """文字列の左側を取り出す。"""
    _chk_argscount(args, 2, "LEFT", line, pos)
    args_r = _all_eval(args)
    s = args_r[0]
    n = args_r[1]
    a = _chk_string(s, "LEFT", 0)
    v = min(int(_chk_minvalue(n, "LEFT", 1)), len(a))
    return StringValue(a[:int(v)], line, pos)


def _func_right(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> StringValue:
    """文字列の右側を取り出す。"""
    _chk_argscount(args, 2, "RIGHT", line, pos)
    args_r = _all_eval(args)
    s = args_r[0]
    n = args_r[1]
    a = _chk_string(s, "RIGHT", 0)
    v = len(a) - min(int(_chk_minvalue(n, "RIGHT", 1)), len(a))
    return StringValue(a[int(v):], line, pos)


def _func_mid(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> StringValue:
    """文字列の[N1-1:N1+N2]の範囲を取り出す。"""
    _chk_argscount2(args, 2, 3, "MID", line, pos)
    args_r = _all_eval(args)
    s = args_r[0]
    n1 = args_r[1]
    a = _chk_string(s, "MID", 0)
    n1value = int(_chk_minvalue(n1, "MID", 1, 1))
    if len(a)+1 <= n1value:
        a = ""
    else:
        v = n1value - 1
        a = a[int(v):]
        if len(args_r) == 3:
            n2 = args_r[2]
            v = min(int(_chk_minvalue(n2, "MID", 2)), len(a))
            a = a[:int(v)]
    return StringValue(a, line, pos)


def _func_str(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> StringValue:
    """引数を文字列に変換する。"""
    _chk_argscount(args, 1, "STR", line, pos)
    args_r = _all_eval(args)
    return StringValue(args_r[0].to_str(), line, pos)


_NUM_REG = re.compile("\\A\\s*-?([0-9]+(\\.[0-9]*)?|([0-9]*\\.)?[0-9]+)\\s*\\Z")


def _func_value(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> DecimalValue:
    """引数を数値化する。"""
    _chk_argscount(args, 1, "VALUE", line, pos)
    args_r = _all_eval(args)
    a = args_r[0]
    if isinstance(a, DecimalValue):
        assert isinstance(a.value, decimal.Decimal)
        value = a.value
    elif isinstance(a, StringValue):
        assert isinstance(a.value, str)
        if not _NUM_REG.match(a.value):
            raise InvalidArgumentException("Invalid argument: %s" % a.value, "VALUE", 0, a.to_str(), a.line, a.pos)
        try:
            value = decimal.Decimal(a.value)
        except Exception:
            raise InvalidArgumentException("Invalid argument: %s" % a.value, "VALUE", 0, a.to_str(), a.line, a.pos)
    else:
        raise InvalidArgumentException("Invalid argument: %s" % a.value, "VALUE", 0, a.to_str(), a.line, a.pos)
    return DecimalValue(value, line, pos)


def _func_int(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> DecimalValue:
    """引数を整数化する。"""
    _chk_argscount(args, 1, "INT", line, pos)
    args_r = _all_eval(args)
    a = args_r[0]
    if isinstance(a, DecimalValue):
        assert isinstance(a.value, decimal.Decimal)
        value = a.value
    elif isinstance(a, StringValue):
        try:
            value = decimal.Decimal(a.value)
        except Exception:
            raise InvalidArgumentException("Invalid argument: %s" % a.value, "INT", 0, a.to_str(), a.line, a.pos)
    else:
        raise InvalidArgumentException("Invalid argument: %s" % a.value, "INT", 0, a.to_str(), a.line, a.pos)
    return DecimalValue(value.to_integral_exact(decimal.ROUND_DOWN), line, pos)


def _func_if(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> ValueType:
    """args[0]がTrueであればargs[1]を、そうでなければargs[2]を返す。"""
    _chk_argscount(args, 3, "IF", line, pos)
    a = args[0]()
    a_bool = _chk_boolean(a, "IF", 0)
    t = args[1]
    f = args[2]
    return t() if a_bool else f()


def _func_var(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> ValueType:
    """汎用変数の値を読む。"""
    _chk_argscount(args, 1, "VAR", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "VAR", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.variants:
        variant = event.variants[path]
    elif path in cw.cwpy.sdata.variants:
        _chk_diffsc(is_differentscenario, line, pos)
        variant = cw.cwpy.sdata.variants[path]
    else:
        raise VariantNotFoundException("Variant \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    if variant.type == "Boolean":
        assert isinstance(variant.value, bool)
        return BooleanValue(variant.value, line, pos)
    elif variant.type == "Number":
        assert isinstance(variant.value, decimal.Decimal)
        return DecimalValue(variant.value, line, pos)
    else:
        assert variant.type == "String"
        assert isinstance(variant.value, str)
        return StringValue(variant.value, line, pos)


def _func_flagvalue(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                    pos: int) -> BooleanValue:
    """フラグの値を読む。"""
    _chk_argscount(args, 1, "FLAGVALUE", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "FLAGVALUE", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.flags:
        flag = event.flags[path]
    elif path in cw.cwpy.sdata.flags:
        _chk_diffsc(is_differentscenario, line, pos)
        flag = cw.cwpy.sdata.flags[path]
    else:
        raise FlagNotFoundException("Flag \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    return BooleanValue(flag.value, line, pos)


def _func_flagtext(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> StringValue:
    """フラグの値の文字列を読む。"""
    _chk_argscount2(args, 1, 2, "FLAGTEXT", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "FLAGTEXT", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.flags:
        flag = event.flags[path]
    elif path in cw.cwpy.sdata.flags:
        _chk_diffsc(is_differentscenario, line, pos)
        flag = cw.cwpy.sdata.flags[path]
    else:
        raise FlagNotFoundException("Flag \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    if len(args_r) == 2:
        value = _chk_boolean(args_r[1], "FLAGTEXT", 1)
    else:
        value = flag.value

    s = flag.get_valuename(value)

    if flag.spchars:
        s, _namelist = cw.sprite.message.rpl_specialstr(s, localvariables=True)

    return StringValue(s, line, pos)


def _func_stepvalue(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                    pos: int) -> DecimalValue:
    """ステップの値を読む。"""
    _chk_argscount(args, 1, "STEPVALUE", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "STEPVALUE", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.steps:
        step = event.steps[path]
    elif path in cw.cwpy.sdata.steps:
        _chk_diffsc(is_differentscenario, line, pos)
        step = cw.cwpy.sdata.steps[path]
    else:
        raise StepNotFoundException("Step \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    return DecimalValue(decimal.Decimal(step.value), line, pos)


def _func_steptext(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> StringValue:
    """ステップの値の文字列を読む。"""
    _chk_argscount2(args, 1, 2, "STEPTEXT", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "STEPTEXT", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.steps:
        step = event.steps[path]
    elif path in cw.cwpy.sdata.steps:
        _chk_diffsc(is_differentscenario, line, pos)
        step = cw.cwpy.sdata.steps[path]
    else:
        raise StepNotFoundException("Step \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    if len(args_r) == 2:
        value = int(_chk_decimal(args_r[1], "STEPTEXT", 1))
    else:
        value = step.value

    if value < 0 or len(step.valuenames) <= value:
        raise InvalidStepValueException("Invalid step value: \"%s\"[%s]" % (path, value), args_r[1].line, args_r[1].pos)

    s = step.get_valuename(value)

    if step.spchars:
        s, _namelist = cw.sprite.message.rpl_specialstr(s, localvariables=True)

    return StringValue(s, line, pos)


def _func_stepmax(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> DecimalValue:
    """ステップの最大値を取得する。"""
    _chk_argscount(args, 1, "STEPMAX", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "STEPMAX", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.steps:
        step = event.steps[path]
    elif path in cw.cwpy.sdata.steps:
        _chk_diffsc(is_differentscenario, line, pos)
        step = cw.cwpy.sdata.steps[path]
    else:
        raise StepNotFoundException("Step \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    return DecimalValue(decimal.Decimal(len(step.valuenames)-1), line, pos)


def _func_dice(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> DecimalValue:
    """ダイスを振って結果の値を返す。"""
    _chk_argscount(args, 2, "DICE", line, pos)
    args_r = _all_eval(args)
    t = int(_chk_minvalue(args_r[0], "DICE", 0))
    s = int(_chk_minvalue(args_r[1], "DICE", 0))
    if t == 0 or s == 0:
        n = 0
    else:
        n = cw.cwpy.dice.roll(t, s)
    return DecimalValue(n, line, pos)


def _func_selected(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                   pos: int) -> DecimalValue:
    """選択メンバのキャラクター番号を数値(1～)で返す。"""
    _chk_argscount(args, 0, "SELECTED", line, pos)
    if cw.cwpy.event.has_selectedmember():
        try:
            ccard = cw.cwpy.event.get_selectedmember()
            if isinstance(ccard, cw.sprite.card.PlayerCard):
                pcards = cw.cwpy.get_pcards()
                n = pcards.index(ccard) + 1
            elif isinstance(ccard, cw.sprite.card.EnemyCard):
                pcards_len = len(cw.cwpy.get_pcards())
                ecards = cw.cwpy.get_ecards()
                n = ecards.index(ccard) + 1 + pcards_len
            elif isinstance(ccard, cw.sprite.card.FriendCard):
                pcards_len = len(cw.cwpy.get_pcards())
                ecards_len = len(cw.cwpy.get_ecards())
                fcards = cw.cwpy.get_fcards()
                n = fcards.index(ccard) + 1 + pcards_len + ecards_len
            else:
                assert False
        except ValueError:
            cw.util.print_ex(file=sys.stderr)
            n = 0
    else:
        n = 0
    return DecimalValue(n, line, pos)


def _ccard_from(arg: ValueType, func_name: str) -> Optional[cw.character.Character]:
    n = int(_chk_minvalue(arg, func_name, 0))
    if n == 0:
        return None
    else:
        index = n - 1
        pcards = cw.cwpy.get_pcards()
        if index < len(pcards):
            return pcards[index]
        index -= len(pcards)
        ecards = cw.cwpy.get_ecards()
        if index < len(ecards):
            return ecards[index]
        index -= len(ecards)
        fcards = cw.cwpy.get_fcards()
        if index < len(fcards):
            return fcards[index]
        return None


def _func_casttype(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                   pos: int) -> DecimalValue:
    """キャラクター番号からキャラクターのタイプ(1=Player,2=Enemy,3=Friend)を返す。"""
    _chk_argscount(args, 1, "CASTTYPE", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "CASTTYPE")
    if isinstance(ccard, cw.character.Player):
        return DecimalValue(1, line, pos)
    elif isinstance(ccard, cw.character.Enemy):
        return DecimalValue(2, line, pos)
    elif isinstance(ccard, cw.character.Friend):
        return DecimalValue(3, line, pos)
    else:
        return DecimalValue(0, line, pos)


def _func_castname(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int, pos: int) -> StringValue:
    """キャラクター番号からキャラクターの名前を返す。"""
    _chk_argscount(args, 1, "CASTNAME", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "CASTNAME")
    if ccard:
        return StringValue(ccard.get_showingname(), line, pos)
    else:
        return StringValue("", line, pos)


def _func_findcoupon(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                     pos: int) -> DecimalValue:
    """キャラクター番号のキャラクターのクーポンを検索してクーポン番号を返す。"""
    _chk_argscount2(args, 2, 3, "FINDCOUPON", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "FINDCOUPON")
    pattern = _chk_string(args_r[1], "FINDCOUPON", 1)
    if len(args_r) < 3:
        startpos = 1
    else:
        startpos = int(_chk_minvalue(args_r[2], "FINDCOUPON", 0))
    if ccard is None:
        return DecimalValue(0, line, pos)
    startindex = startpos - 1
    if startindex < 0 or ccard.coupons_len() <= startindex:
        return DecimalValue(0, line, pos)
    reg = re.compile(fnmatch.translate(pattern))
    index = ccard.find_coupon(lambda name: bool(reg.match(name)), startindex)
    return DecimalValue(index + 1, line, pos)


def _func_coupontext(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                     pos: int) -> StringValue:
    """キャラクター番号のキャラクターの所持するクーポン名を返す。"""
    _chk_argscount(args, 2, "COUPONTEXT", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "COUPONTEXT")
    index_d = _chk_minvalue(args_r[1], "COUPONTEXT", 0)
    if ccard is None:
        return StringValue("", line, pos)
    index = int(index_d) - 1
    if index < 0 or ccard.coupons_len() <= index:
        return StringValue("", line, pos)
    return StringValue(ccard.get_coupon_at(index)[0], line, pos)


def _func_findgossip(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                     pos: int) -> DecimalValue:
    """ゴシップを検索してゴシップ番号を返す。"""
    _chk_argscount2(args, 1, 2, "FINDGOSSIP", line, pos)
    args_r = _all_eval(args)
    pattern = _chk_string(args_r[0], "FINDGOSSIP", 0)
    if len(args_r) < 2:
        startpos = 1
    else:
        startpos = int(_chk_minvalue(args_r[1], "FINDGOSSIP", 0))
    startindex = startpos - 1
    if cw.cwpy.ydata is None or startindex < 0 or cw.cwpy.ydata.gossips_len() <= startindex:
        return DecimalValue(0, line, pos)
    reg = re.compile(fnmatch.translate(pattern))
    index = cw.cwpy.ydata.find_gossip(lambda name: bool(reg.match(name)), startindex)
    return DecimalValue(index + 1, line, pos)


def _func_gossiptext(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                     pos: int) -> StringValue:
    """ゴシップ名を返す。"""
    _chk_argscount(args, 1, "GOSSIPTEXT", line, pos)
    args_r = _all_eval(args)
    index = int(_chk_minvalue(args_r[0], "GOSSIPTEXT", 0)) - 1
    if cw.cwpy.ydata is None or index < 0 or cw.cwpy.ydata.gossips_len() <= index:
        return StringValue("", line, pos)
    return StringValue(cw.cwpy.ydata.get_gossip_at(index), line, pos)


def _func_partyname(args: List[Callable[[], ValueType]], is_differentscenario: bool, line: int,
                    pos: int) -> StringValue:
    """パーティ名を返す。"""
    _chk_argscount(args, 0, "PARTYNAME", line, pos)
    if cw.cwpy.ydata is None or cw.cwpy.ydata.party is None:
        return StringValue("", line, pos)
    return StringValue(cw.cwpy.ydata.party.get_showingname(), line, pos)


_functions = {
    "len": _func_len,
    "find": _func_find,
    "left": _func_left,
    "right": _func_right,
    "mid": _func_mid,
    "str": _func_str,
    "value": _func_value,
    "int": _func_int,
    "if": _func_if,
    "dice": _func_dice,
    "max": _func_max,
    "min": _func_min,
    "var": _func_var,
    "flagvalue": _func_flagvalue,
    "flagtext": _func_flagtext,
    "stepvalue": _func_stepvalue,
    "steptext": _func_steptext,
    "stepmax": _func_stepmax,
    "selected": _func_selected,
    "casttype": _func_casttype,
    "castname": _func_castname,
    "findcoupon": _func_findcoupon,
    "coupontext": _func_coupontext,
    "findgossip": _func_findgossip,
    "gossiptext": _func_gossiptext,
    "partyname": _func_partyname,
}

assert calculate(parse("--5")).value == 5
assert calculate(parse("---5")).value == -5
assert calculate(parse("-(--5)")).value == -5
assert calculate(parse("-- min(100,23)+5")).value == 28
assert calculate(parse("+-Min(100,23)+ - 5")).value == -28
assert calculate(parse("max (45, 42, 100.5,  23 ) + 0.123")).value == decimal.Decimal("100.623")
assert calculate(parse("mAX(45,42,100.5,23)+0.123 = 100.623")).value is True
assert calculate(parse("max(45,42,100.5,23)+0.123 <> 100.623")).value is False
assert calculate(parse("true or false")).value is True
assert calculate(parse("tRUe and faLSE")).value is False
assert calculate(parse("true and true or false and false")).value is True
assert calculate(parse("((true and true) or false) and false")).value is False
assert calculate(parse("not false and true or false and false")).value is True
assert calculate(parse("not false or false")).value is True
assert calculate(parse("not not (false or false)")).value is False
assert calculate(parse("not not not true")).value is False
assert calculate(parse("not 1 = 2")).value is True
assert calculate(parse("not 1 + 2 = 3")).value is False
assert calculate(parse("nOT False And tRUe oR FALSE aND faLse")).value is True
assert calculate(parse("NOT 1 + 2 = 3")).value is False
assert calculate(parse("nOt 1 + 2 = 3")).value is False
assert calculate(parse("(not true) ~ \"&\" ~ (not true)")).value == "FALSE&FALSE"
assert calculate(parse("(5+8) % 3")).value == 1
assert calculate(parse("5 + 8%3")).value == 7
assert calculate(parse("-2+22*2")).value == 42
assert calculate(parse("9/3")).value == 3
assert calculate(parse("4<=5")).value is True
assert calculate(parse("4<=4")).value is True
assert calculate(parse("4<=3")).value is False
assert calculate(parse("5>=4")).value is True
assert calculate(parse("4>=4")).value is True
assert calculate(parse("3>=4")).value is False
assert calculate(parse("4<5")).value is True
assert calculate(parse("4<4")).value is False
assert calculate(parse("4<3")).value is False
assert calculate(parse("5>4")).value is True
assert calculate(parse("4>4")).value is False
assert calculate(parse("3>4")).value is False
assert calculate(parse("5=4")).value is False
assert calculate(parse("4=4")).value is True
assert calculate(parse("3=4")).value is False
assert calculate(parse("5<>4")).value is True
assert calculate(parse("4<>4")).value is False
assert calculate(parse("3<>4")).value is True
assert calculate(parse("LEN(\"TESTあいうえお\")")).value == 9
assert calculate(parse("FIND(\"対象文字列\", \"対象文字列\")")).value == 1
assert calculate(parse("FIND(\"文字\", \"対象文字列\")")).value == 3
assert calculate(parse("FIND(\"文じ\", \"対象文字列\")")).value == 0
assert calculate(parse("FIND(\"文字\", \"対象文字列\", 3)")).value == 3
assert calculate(parse("FIND(\"文字\", \"対象文字列\", 4)")).value == 0
assert calculate(parse("FIND(\"文字\", \"対象文字列\", 0)")).value == 0
assert calculate(parse("FIND(\"列\", \"対象文字列\", 5)")).value == 5
assert calculate(parse("FIND(\"列\", \"対象文字列\", 6)")).value == 0
assert calculate(parse("FIND(\"\", \"対象文字列\")")).value == 1
assert calculate(parse("FIND(\"\", \"対象文字列\", 5)")).value == 5
assert calculate(parse("FIND(\"\", \"対象文字列\", 6)")).value == 0
assert calculate(parse("FIND(\"字\", \"A象B文C字D列\")")).value == 6
assert calculate(parse("FIND(\"字\", \"A象B文C字D列\", 6)")).value == 6
assert calculate(parse("FIND(\"字\", \"A象B文C字D列\", 7)")).value == 0
assert calculate(parse("FIND(\"\", \"\")")).value == 0
assert calculate(parse("find(\"列\", \"対象文字列\", 5)")).value == 5
assert calculate(parse("fIND(\"列\", \"対象文字列\", 5)")).value == 5
assert calculate(parse("LEFT(\"あいうえお\", 0)")).value == ""
assert calculate(parse("LEFT(\"あいうえお\", 3)")).value == "あいう"
assert calculate(parse("LEFT(\"あいうえお\", 8)")).value == "あいうえお"
assert calculate(parse("LEFT(\"あいうえお\", 8)")).value == "あいうえお"
assert calculate(parse("Left(\"あいうえお\", 8)")).value == "あいうえお"
assert calculate(parse("RIGHT(\"あいうえお\", 0)")).value == ""
assert calculate(parse("RIGHT(\"あいうえお\", 3)")).value == "うえお"
assert calculate(parse("RIGHT(\"あいうえお\", 8)")).value == "あいうえお"
assert calculate(parse("right(\"あいうえお\", 8)")).value == "あいうえお"
assert calculate(parse("MID(\"あいうえお\", 2, 3)")).value == "いうえ"
assert calculate(parse("MID(\"あいうえお\", 5, 3)")).value == "お"
assert calculate(parse("MID(\"あいうえお\", 6, 3)")).value == ""
assert calculate(parse("MID(\"あいうえお\", 3)")).value == "うえお"
assert calculate(parse("MID(\"あいうえお\", 5)")).value == "お"
assert calculate(parse("MID(\"あいうえお\", 6)")).value == ""
assert calculate(parse("MID(\"あいうえお\", 7)")).value == ""
assert calculate(parse("mId(\"あいうえお\", 7)")).value == ""
assert calculate(parse("STR(\"あいうえお\")")).value == "あいうえお"
assert calculate(parse("STR(42)")).value == "42"
assert calculate(parse("STR(42.42 + 5)")).value == "47.42"
assert calculate(parse("sTR(42.42 + 5)")).value == "47.42"
assert calculate(parse("VALUE(42.42 + 5)")).value == decimal.Decimal("47.42")
assert calculate(parse("VALUE(42)")).value == 42
assert calculate(parse("VALUE(\"42\")")).value == 42
assert calculate(parse("VALUE(\"42.123\")")).value == decimal.Decimal("42.123")
assert calculate(parse("VAluE(\"42.123\")")).value == decimal.Decimal("42.123")
assert calculate(parse("INT(\"42.123\")")).value == 42
assert calculate(parse("INT(\"42.9\")")).value == 42
assert calculate(parse("INT(\" -42.9  \")")).value == -42
assert calculate(parse("int(\" -42.9  \")")).value == -42
assert calculate(parse("IF(1=2,99,88)")).value == 88
assert calculate(parse("IF(2=2,99,88)")).value == 99
assert calculate(parse("If(2=2,99,88)")).value == 99
try:
    assert calculate(parse("5 / (2-1-1)"))
    assert False
except ZeroDivisionException:
    pass
try:
    assert calculate(parse("5 % (2-1-1)"))
    assert False
except ZeroDivisionException:
    pass
try:
    assert calculate(parse("MAX()"))
    assert False
except ArgumentsCountException:
    pass


def main() -> None:
    st = parse(" ".join(sys.argv[1:]))
    print(st)
    print(calculate(st))


if __name__ == "__main__":
    main()
