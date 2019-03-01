#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import decimal

import cw


class ComputeException(Exception):
    """式の中で発生する何らかのエラー。"""
    def __init__(self, msg, line, pos):
        Exception.__init__(self, msg + " Line: %s, Pos: %s" % (line, pos))
        self.line = line
        self.pos = pos


class TokanizeException(ComputeException):
    """字句解析エラー。"""
    def __init__(self, msg, line, pos):
        ComputeException.__init__(self, msg, line, pos)


class SemanticsException(ComputeException):
    """構文解析エラー。"""
    def __init__(self, msg, line, pos):
        ComputeException.__init__(self, msg, line, pos)


class ZeroDivisionException(ComputeException):
    """ゼロで割ろうとした。"""
    def __init__(self, msg, line, pos):
        Exception.__init__(self, msg + " Line: %s, Pos: %s" % (line, pos))
        self.line = line
        self.pos = pos


class FunctionIsNotDefinedException(ComputeException):
    """関数未定義エラー。"""
    def __init__(self, msg, func_name, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name


class ArgumentIsNotDecimalException(ComputeException):
    """関数の引数が数値でない。"""
    def __init__(self, msg, func_name, arg_index, arg_value, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class ArgumentIsNotStringException(ComputeException):
    """関数の引数が文字列でない。"""
    def __init__(self, msg, func_name, arg_index, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index


class ArgumentIsNotBooleanException(ComputeException):
    """関数の引数が真偽値でない。"""
    def __init__(self, msg, func_name, arg_index, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index


class ArgumentsCountException(ComputeException):
    """関数の引数の数が誤っている。"""
    def __init__(self, msg, func_name, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name


class InvalidArgumentException(ComputeException):
    """関数の引数が誤っている。"""
    def __init__(self, msg, func_name, arg_index, arg_value, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class VariantNotFoundException(ComputeException):
    """汎用変数が存在しない。"""
    def __init__(self, msg, path, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.path = path


class FlagNotFoundException(ComputeException):
    """フラグが存在しない。"""
    def __init__(self, msg, path, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.path = path


class StepNotFoundException(ComputeException):
    """ステップが存在しない。"""
    def __init__(self, msg, path, line, pos):
        ComputeException.__init__(self, msg, line, pos)
        self.path = path


class InvalidStepValueException(ComputeException):
    """ステップ値が範囲外。"""
    def __init__(self, msg, line, pos):
        ComputeException.__init__(self, msg, line, pos)


class DifferentScenarioException(ComputeException):
    """外部シナリオで状態変数を読もうとした。"""
    def __init__(self, msg, line, pos):
        ComputeException.__init__(self, msg, line, pos)


class Function(object):
    """関数の名前と引数を保持し、計算を行う。"""
    def __init__(self, name, line, pos, args):
        self.name = name.lower()
        self.line = line
        self.pos = pos
        self.args = args

    def call(self, is_differentscenario):
        args = []
        for arg in self.args:
            args.append(calculate(arg, is_differentscenario))
        name = self.name
        if name in _functions:
            return _functions[name](args, is_differentscenario, self.line, self.pos)
        else:
            raise FunctionIsNotDefinedException("Function is not defined." % name, name, self.line, self.pos)

    def __repr__(self):
        return "%s(%s)" % (self.name, ", ".join([str(a) for a in self.args]))


class UnaryOperator(object):
    """単項演算子の保持と実行を行う。"""
    def __init__(self, operator, line, pos):
        self.operator = operator
        self.line = line
        self.pos = pos

    def call(self, rhs):
        o = self.operator
        if o == '+':
            if not isinstance(rhs, DecimalValue): raise SemanticsException("value [%s] is not number." % rhs.value, rhs.line, rhs.pos)
            return DecimalValue(rhs.value, self.line, self.pos)
        elif o == '-':
            if not isinstance(rhs, DecimalValue): raise SemanticsException("value [%s] is not number." % rhs.value, rhs.line, rhs.pos)
            return DecimalValue(-rhs.value, self.line, self.pos)
        elif o == "not":
            if not isinstance(rhs, BooleanValue): raise SemanticsException("value [%s] is not boolean." % rhs.value, rhs.line, rhs.pos)
            return BooleanValue(not rhs.value, self.line, self.pos)
        else:
            raise SemanticsException("Invalid operator: %s" % o, self.line, self.pos)

    def __repr__(self):
        return "UOp(%s, %s:%s)" % (self.operator, self.line, self.pos)


class Operator(object):
    """二項演算子の保持と実行を行う。"""
    def __init__(self, operator, line, pos):
        self.operator = operator
        self.line = line
        self.pos = pos

    def call(self, lhs, rhs):
        o = self.operator
        def chk_num():
            if not isinstance(lhs, DecimalValue): raise SemanticsException("lhs [%s] is not number." % lhs.value, lhs.line, lhs.pos)
            if not isinstance(rhs, DecimalValue): raise SemanticsException("rhs [%s] is not number." % rhs.value, rhs.line, rhs.pos)
        def chk_bool():
            if not isinstance(lhs, BooleanValue): raise SemanticsException("lhs [%s] is not boolean." % lhs.value, lhs.line, lhs.pos)
            if not isinstance(rhs, BooleanValue): raise SemanticsException("rhs [%s] is not boolean." % rhs.value, rhs.line, rhs.pos)
        if o == '+':
            chk_num()
            return DecimalValue(lhs.value + rhs.value, self.line, self.pos)
        elif o == '-':
            chk_num()
            return DecimalValue(lhs.value - rhs.value, self.line, self.pos)
        elif o == '*':
            chk_num()
            return DecimalValue(lhs.value * rhs.value, self.line, self.pos)
        elif o == '/':
            chk_num()
            if rhs.value == 0:
                raise ZeroDivisionException("Division by zero.", self.line, self.pos)
            return DecimalValue(lhs.value / rhs.value, self.line, self.pos)
        elif o == '%':
            chk_num()
            if rhs.value == 0:
                raise ZeroDivisionException("Division by zero.", self.line, self.pos)
            return DecimalValue(lhs.value % rhs.value, self.line, self.pos)
        elif o == '~':
            return StringValue(lhs.to_str() + rhs.to_str(), self.line, self.pos)
        elif o == "<=":
            chk_num()
            return BooleanValue(lhs.value <= rhs.value, self.line, self.pos)
        elif o == ">=":
            chk_num()
            return BooleanValue(lhs.value >= rhs.value, self.line, self.pos)
        elif o == "<":
            chk_num()
            return BooleanValue(lhs.value < rhs.value, self.line, self.pos)
        elif o == ">":
            chk_num()
            return BooleanValue(lhs.value > rhs.value, self.line, self.pos)
        elif o in ("=", "<>"):
            if isinstance(lhs, StringValue) or isinstance(rhs, StringValue):
                r = lhs.to_str() == rhs.to_str()
            elif isinstance(lhs, BooleanValue) or isinstance(rhs, BooleanValue):
                chk_bool()
                r = lhs.value == rhs.value
            else:
                chk_num()
                r = lhs.value == rhs.value
            if o == "<>":
                r = not r
            return BooleanValue(r, self.line, self.pos)
        elif o == "and":
            chk_bool()
            return BooleanValue(lhs.value and rhs.value, self.line, self.pos)
        elif o == "or":
            chk_bool()
            return BooleanValue(lhs.value or rhs.value, self.line, self.pos)
        else:
            raise SemanticsException("Invalid operator: %s" % o, self.line, self.pos)

    def __repr__(self):
        return "Op(%s, %s:%s)" % (self.operator, self.line, self.pos)


class Token(object):
    """行+行内位置を伴うトークン情報。"""
    def __init__(self, token, line, pos):
        self.token = token
        self.line = line
        self.pos = pos

    def __repr__(self):
        return "Token(%s, %s:%s)" % (self.token, self.line, self.pos)


class DecimalValue(object):
    """数値トークン。"""
    def __init__(self, s, line, pos):
        self.value = decimal.Decimal(s)
        self.line = line
        self.pos = pos

    def to_str(self):
        return str(self.value)

    def __repr__(self):
        return "Decimal(%s)" % self.value


class StringValue(object):
    """文字列トークン。"""
    def __init__(self, s, line, pos):
        self.value = s
        self.line = line
        self.pos = pos

    def to_str(self):
        return self.value

    def __repr__(self):
        return "String(\"%s\")" % self.value


class BooleanValue(object):
    """真偽値トークン。"""
    def __init__(self, s, line, pos):
        self.value = s
        self.line = line
        self.pos = pos

    def to_str(self):
        return "True" if self.value else "False"

    def __repr__(self):
        return "Boolean(\"%s\")" % self.value


def parse(s):
    """文字列sを式として解析し、スタックを生成する。"""
    tokens = []
    bpos = 0
    bm = None
    line = 1
    pos = 1
    for m in re.finditer("[0-9]+(\\.[0-9]+)?|[a-z_][a-z_0-9]*|[\+\-\*\/\%\~]|[\(\)]|,|\\$?\"([^\\\"]|\"\")*\"|or|and|<=|>=|<>|<|>|=|true|false|\\n|\\s+", s, re.I):
        if bpos is None or m.start() != bpos:
            raise TokanizeException("Invalid Character: %s" % s[bm.end():m.start()], line, pos)
        bpos = m.end()
        t = m.group()
        l = cw.util.get_strlen(t)
        if not t.isspace():
            tokens.append(Token(t, line, pos))
        bm = m
        if t == "\n":
            line += 1
            pos = 1
        else:
            pos += l


    def parse_arguments(tokens, i):
        if len(tokens) <= i + 1: raise SemanticsException("Invalid function call.", tokens[i].line, tokens[i].pos)
        i += 1
        t = tokens[i].token
        if not t in ('('): raise SemanticsException("Need an open parenthesis here.", tokens[i].line, tokens[i].pos)
        args = []
        while i + 1 < len(tokens) and tokens[i].token != ')':
            i, arg = parse_semantics(tokens, i + 1)
            args.append(arg)
        return i + 1, args


    def parse_semantics(tokens, i):
        num = []
        op = []

        isop = True
        parlevel = 0

        while i < len(tokens):
            t = tokens[i].token
            line = tokens[i].line
            pos = tokens[i].pos
            unary = False
            if t == "not":
                if not isop: raise SemanticsException("Need a symbol or number here.", line, pos)
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
                if isop: raise SemanticsException("Need a symbol or number here.", line, pos)
                # 連結子
                oplevel = 4
            elif t in ('/', '*', '%'):
                if isop: raise SemanticsException("Need a symbol or number here.", line, pos)
                # 優先の高い演算子
                oplevel = 5
            elif t in ("<=", ">=", "<>", "<", ">", "="):
                if isop: raise SemanticsException("Need a symbol or number here.", line, pos)
                # 比較演算子
                oplevel = 3
            elif t.lower() == "and":
                if isop: raise SemanticsException("Need a symbol or number here.", line, pos)
                # AND演算子
                oplevel = 1
            elif t.lower() == "or":
                if isop: raise SemanticsException("Need a symbol or number here.", line, pos)
                # OR演算子
                oplevel = 0
            elif t in ('('):
                if not isop: raise SemanticsException("Need an operator here.", line, pos)
                # 開き括弧
                parlevel += 1
                i += 1
                continue
            elif t in (')'):
                if isop: raise SemanticsException("Need a symbol or number here.", line, pos)
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
                if not isop: raise SemanticsException("Need an operator here.", line, pos)
                # 数値
                num.append(DecimalValue(t, line, pos))
                isop = False
                i += 1
                continue
            elif t[0] in ('"'):
                if not isop: raise SemanticsException("Need an operator here.", line, pos)
                # 文字列
                assert t[-1] == '"'
                num.append(StringValue(t[1:-1].replace('""', '"'), line, pos))
                isop = False
                i += 1
                continue
            elif t[0] in ('$'):
                if not isop: raise SemanticsException("Need an operator here.", line, pos)
                # 汎用変数
                assert t[1] == '"'
                assert t[-1] == '"'
                num.append(Function("var", line, pos, [[StringValue(t[2:-1].replace('""', '"'), line, pos)]]))
                isop = False
                i += 1
                continue
            elif t.lower() in ("true", "false"):
                if not isop: raise SemanticsException("Need an operator here.", line, pos)
                # 真偽値
                num.append(BooleanValue(t.lower() == "true", line, pos))
                isop = False
                i += 1
                continue
            else:
                if not isop: raise SemanticsException("Need an operator here.", line, pos)
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
    if i != len(tokens): raise SemanticsException("Invalid semantics.", line, pos)
    return num


def calculate(st, is_differentscenario=False):
    """スタックstの式を実行する。"""
    op = []
    for t in st:
        if isinstance(t, Function):
            # 関数呼び出し
            v = t.call(is_differentscenario)
        elif isinstance(t, UnaryOperator):
            # 単項演算子
            rhs = op.pop()
            v = t.call(rhs)
        elif isinstance(t, Operator):
            # 二項演算子
            rhs = op.pop()
            lhs = op.pop()
            v = t.call(lhs, rhs)
        else:
            # 数値
            v = t
        op.append(v)
    return op.pop(-1)


def eval(st, is_differentscenario):
    return cw.data.Variant(calculate(st, is_differentscenario).value, "", "")


def _chk_diffsc(is_differentscenario):
    if is_differentscenario:
        raise DifferentScenarioException("Read a variable at different scenario.", line, pos)


def _chk_argscount(args, n, func_name):
    if len(args) != n:
        raise ArgumentsCountException("Invalid arguments count: %s != %s" % (n, len(args)), func_name, line, pos)


def _chk_decimal(arg, func_name, arg_index):
    """argがDecimalValueか調べる。"""
    if not isinstance(arg, DecimalValue):
        raise ArgumentIsNotDecimalException("%s is not Decimal." % arg.value, func_name, arg_index, arg.to_str(), arg.line, arg.pos)


def _chk_minvalue(arg, func_name, arg_index, minvalue=0):
    """argが0以上のDecimalValueか調べる。"""
    _chk_decimal(arg, func_name, arg_index)
    if arg.value < minvalue:
        raise InvalidArgumentException("%s < %s." % (arg.value, minvalue), func_name, arg_index, arg.to_str(), arg.line, arg.pos)


def _chk_string(arg, func_name, arg_index):
    """argがStringValueか調べる。"""
    if not isinstance(arg, StringValue):
        raise ArgumentIsNotStringException("%s is not String." % arg.value, func_name, arg_index, arg.line, arg.pos)


def _chk_boolean(arg, func_name, arg_index):
    """argがBooleanValueか調べる。"""
    if not isinstance(arg, BooleanValue):
        raise ArgumentIsNotBooleanException("%s is not Boolean." % arg.value, func_name, arg_index, arg.line, arg.pos)


def _is_alldecimal(args, func_name):
    """argsが全てDecimalValueで構成されているか検査する。"""
    for i, arg in enumerate(args):
        _chk_decimal(arg, func_name, i)
    return True


def _func_max(args, is_differentscenario, line, pos):
    """MAX関数を実行する。"""
    if len(args) and _is_alldecimal(args, "MAX"):
        return DecimalValue(max(*map(lambda a: a.value, args)) if 1 < len(args) else args[0].value, line, pos)
    raise ArgumentsCountException("No argments of max.", "MAX", line, pos)


def _func_min(args, is_differentscenario, line, pos):
    """MIN関数を実行する。"""
    if len(args) and _is_alldecimal(args, "MIN"):
        return DecimalValue(min(*map(lambda a: a.value, args)) if 1 < len(args) else args[0].value, line, pos)
    raise ArgumentsCountException("No argments of min.", "MIN", line, pos)


def _func_len(args, is_differentscenario, line, pos):
    """文字列の文字数を返す。"""
    _chk_argscount(args, 1, "LEN")
    a = args[0]
    _chk_string(a, "LEN", 0)
    return DecimalValue(len(a.value), line, pos)


def _func_left(args, is_differentscenario, line, pos):
    """文字列の左側を取り出す。"""
    _chk_argscount(args, 2, "LEFT")
    s = args[0]
    n = args[1]
    _chk_string(s, "LEFT", 0)
    _chk_minvalue(n, "LEFT", 1)
    a = s.value
    v = min(n.value, len(a))
    return StringValue(a[:int(v)], line, pos)


def _func_right(args, is_differentscenario, line, pos):
    """文字列の右側を取り出す。"""
    _chk_argscount(args, 2, "RIGHT")
    s = args[0]
    n = args[1]
    _chk_string(s, "RIGHT", 0)
    _chk_minvalue(n, "RIGHT", 1)
    a = s.value
    v = len(a) - min(n.value, len(a))
    return StringValue(a[int(v):], line, pos)


def _func_mid(args, is_differentscenario, line, pos):
    """文字列の[N1-1:N1+N2]の範囲を取り出す。"""
    _chk_argscount(args, 3, "MID")
    s = args[0]
    n1 = args[1]
    n2 = args[2]
    _chk_string(s, "MID", 0)
    _chk_minvalue(n1, "MID", 1, 1)
    _chk_minvalue(n2, "MID", 2)
    a = s.value
    if len(a)+1 <= n1.value:
        a = ""
    else:
        v = n1.value - 1
        a = a[int(v):]
        v = min(n2.value, len(a))
        a = a[:int(v)]
    return StringValue(a, line, pos)


def _func_str(args, is_differentscenario, line, pos):
    """引数を文字列に変換する。"""
    _chk_argscount(args, 1, "STR")
    return StringValue(args[0].to_str(), line, pos)


def _func_value(args, is_differentscenario, line, pos):
    """引数を数値化する。"""
    _chk_argscount(args, 1, "VALUE")
    a = args[0]
    if isinstance(a, DecimalValue):
        value = a.value
    elif isinstance(a, StringValue):
        try:
            value = decimal.Decimal(a.value)
        except:
            raise InvalidArgumentException("Invalid argument: %s" % a.value, "VALUE", 0, a.to_str(), a.line, a.pos)
    else:
        raise InvalidArgumentException("Invalid argument: %s" % a.value, "VALUE", 0, a.to_str(), a.line, a.pos)
    return DecimalValue(value, line, pos)


def _func_int(args, is_differentscenario, line, pos):
    """引数を数値化する。"""
    _chk_argscount(args, 1, "INT")
    a = args[0]
    if isinstance(a, DecimalValue):
        value = a.value
    elif isinstance(a, StringValue):
        try:
            value = decimal.Decimal(a.value)
        except:
            raise InvalidArgumentException("Invalid argument: %s" % a.value, "VALUE", 0, a.to_str(), a.line, a.pos)
    else:
        raise InvalidArgumentException("Invalid argument: %s" % a.value, "VALUE", 0, a.to_str(), a.line, a.pos)
    return DecimalValue(value.to_integral_exact(decimal.ROUND_DOWN), line, pos)


def _func_if(args, is_differentscenario, line, pos):
    """args[0]がTrueであればargs[1]を、そうでなければargs[2]を返す。"""
    _chk_argscount(args, 3, "IF")
    a = args[0]
    _chk_boolean(a, "IF", 0)
    t = args[1]
    f = args[2]
    return t if a.value else f


def _func_var(args, is_differentscenario, line, pos):
    """汎用変数の値を読む。"""
    _chk_diffsc(is_differentscenario)
    _chk_argscount(args, 1, "VAR")
    _chk_string(args[0], "VAR", 0)
    path = args[0].value
    if not path in cw.cwpy.sdata.variants:
        raise VariantNotFoundException("Variant \"%s\" is not found.", path, args[0].line, args[0].pos)
    variant = cw.cwpy.sdata.variants[path]
    if variant.type == "Boolean":
        return BooleanValue(variant.value, line, pos)
    elif variant.type == "Number":
        return DecimalValue(variant.value, line, pos)
    else: # String
        return StringValue(variant.value, line, pos)


def _func_flagvalue(args, is_differentscenario, line, pos):
    """フラグの値を読む。"""
    _chk_diffsc(is_differentscenario)
    _chk_argscount(args, 1, "FLAGVALUE")
    _chk_string(args[0], "FLAGVALUE", 0)
    path = args[0].value
    if not path in cw.cwpy.sdata.flags:
        raise FlagNotFoundException("Flag \"%s\" is not found.", path, args[0].line, args[0].pos)
    flag = cw.cwpy.sdata.flags[path]
    return BooleanValue(flag.value, line, pos)


def _func_flagtext(args, is_differentscenario, line, pos):
    """フラグの値の文字列を読む。"""
    _chk_diffsc(is_differentscenario)
    if not len(args) in (1, 2):
        raise ArgumentsCountException("Invalid arguments count: 1-2 != %s" % len(args), "FLAGTEXT", line, pos)
    _chk_string(args[0], "FLAGTEXT", 0)
    path = args[0].value
    if not path in cw.cwpy.sdata.flags:
        raise FlagNotFoundException("Flag \"%s\" is not found.", path, args[0].line, args[0].pos)
    flag = cw.cwpy.sdata.flags[path]

    if len(args) == 2:
        _chk_boolean(args[1], "FLAGTEXT", 1)
        value = args[1].value
    else:
        value = flag.value

    return StringValue(flag.get_valuename(value), line, pos)


def _func_stepvalue(args, is_differentscenario, line, pos):
    """ステップの値を読む。"""
    _chk_diffsc(is_differentscenario)
    _chk_argscount(args, 1, "STEPVALUE")
    _chk_string(args[0], "STEPVALUE", 0)
    path = args[0].value
    if not path in cw.cwpy.sdata.steps:
        raise StepNotFoundException("Step \"%s\" is not found.", path, args[0].line, args[0].pos)
    step = cw.cwpy.sdata.steps[path]
    return DecimalValue(decimal.Decimal(step.value), line, pos)


def _func_steptext(args, is_differentscenario, line, pos):
    """ステップの値の文字列を読む。"""
    _chk_diffsc(is_differentscenario)
    if not len(args) in (1, 2):
        raise ArgumentsCountException("Invalid arguments count: 1-2 != %s" % len(args), "STEPTEXT", line, pos)
    _chk_string(args[0], "STEPTEXT", 0)
    path = args[0].value
    if not path in cw.cwpy.sdata.steps:
        raise StepNotFoundException("Step \"%s\" is not found.", path, args[0].line, args[0].pos)
    step = cw.cwpy.sdata.steps[path]

    if len(args) == 2:
        _chk_decimal(args[1], "STEPTEXT", 1)
        value = args[1].value
    else:
        value = step.value

    if value < 0 or len(step.valuenames) <= value:
        raise InvalidStepValueException("Invalid step value: \"%s\"[%s]" % (path, value), args[1].line, args[1].pos)

    return StringValue(step.get_valuename(value), line, pos)


def _func_stepmax(args, is_differentscenario, line, pos):
    """ステップの最大値を取得する。"""
    _chk_diffsc(is_differentscenario)
    _chk_argscount(args, 1, "STEPMAX")
    _chk_string(args[0], "STEPMAX", 0)
    path = args[0].value
    if not path in cw.cwpy.sdata.steps:
        raise StepNotFoundException("Step \"%s\" is not found.", path, args[0].line, args[0].pos)
    step = cw.cwpy.sdata.steps[path]
    return DecimalValue(decimal.Decimal(len(step.valuenames)), line, pos)


_functions = {
    "len": _func_len,
    "left": _func_left,
    "right": _func_right,
    "mid": _func_mid,
    "str": _func_str,
    "value": _func_value,
    "int": _func_int,
    "if": _func_if,
    "max": _func_max,
    "min": _func_min,
    "var": _func_var,
    "flagvalue": _func_flagvalue,
    "flagtext": _func_flagtext,
    "stepvalue": _func_stepvalue,
    "steptext": _func_steptext,
    "stepmax": _func_stepmax,
}

assert calculate(parse("--5")).value == 5
assert calculate(parse("---5")).value == -5
assert calculate(parse("-(--5)")).value == -5
assert calculate(parse("-- min(100,23)+5")).value == 28
assert calculate(parse("+-Min(100,23)+ - 5")).value == -28
assert calculate(parse("max (45, 42, 100.5,  23 ) + 0.123")).value == decimal.Decimal("100.623")
assert calculate(parse("mAX(45,42,100.5,23)+0.123 = 100.623")).value == True
assert calculate(parse("max(45,42,100.5,23)+0.123 <> 100.623")).value == False
assert calculate(parse("true or false")).value == True
assert calculate(parse("tRUe and faLSE")).value == False
assert calculate(parse("true and true or false and false")).value == True
assert calculate(parse("((true and true) or false) and false")).value == False
assert calculate(parse("not false and true or false and false")).value == True
assert calculate(parse("not false or false")).value == True
assert calculate(parse("not not (false or false)")).value == False
assert calculate(parse("not not not true")).value == False
assert calculate(parse("not 1 = 2")).value == True
assert calculate(parse("not 1 + 2 = 3")).value == False
assert calculate(parse("(not true) ~ \"&\" ~ (not true)")).value == "False&False"
assert calculate(parse("(5+8) % 3")).value == 1
assert calculate(parse("5 + 8%3")).value == 7
assert calculate(parse("-2+22*2")).value == 42
assert calculate(parse("9/3")).value == 3
assert calculate(parse("4<=5")).value == True
assert calculate(parse("4<=4")).value == True
assert calculate(parse("4<=3")).value == False
assert calculate(parse("5>=4")).value == True
assert calculate(parse("4>=4")).value == True
assert calculate(parse("3>=4")).value == False
assert calculate(parse("4<5")).value == True
assert calculate(parse("4<4")).value == False
assert calculate(parse("4<3")).value == False
assert calculate(parse("5>4")).value == True
assert calculate(parse("4>4")).value == False
assert calculate(parse("3>4")).value == False
assert calculate(parse("5=4")).value == False
assert calculate(parse("4=4")).value == True
assert calculate(parse("3=4")).value == False
assert calculate(parse("5<>4")).value == True
assert calculate(parse("4<>4")).value == False
assert calculate(parse("3<>4")).value == True
assert calculate(parse("LEN(\"TESTあいうえお\")")).value == 9
assert calculate(parse("LEFT(\"あいうえお\", 0)")).value == ""
assert calculate(parse("LEFT(\"あいうえお\", 3)")).value == "あいう"
assert calculate(parse("LEFT(\"あいうえお\", 8)")).value == "あいうえお"
assert calculate(parse("RIGHT(\"あいうえお\", 0)")).value == ""
assert calculate(parse("RIGHT(\"あいうえお\", 3)")).value == "うえお"
assert calculate(parse("RIGHT(\"あいうえお\", 8)")).value == "あいうえお"
assert calculate(parse("MID(\"あいうえお\", 2, 3)")).value == "いうえ"
assert calculate(parse("MID(\"あいうえお\", 5, 3)")).value == "お"
assert calculate(parse("MID(\"あいうえお\", 6, 3)")).value == ""
assert calculate(parse("STR(\"あいうえお\")")).value == "あいうえお"
assert calculate(parse("STR(42)")).value == "42"
assert calculate(parse("STR(42.42 + 5)")).value == "47.42"
assert calculate(parse("VALUE(42.42 + 5)")).value == decimal.Decimal("47.42")
assert calculate(parse("VALUE(42)")).value == 42
assert calculate(parse("VALUE(\"42\")")).value == 42
assert calculate(parse("VALUE(\"42.123\")")).value == decimal.Decimal("42.123")
assert calculate(parse("INT(\"42.123\")")).value == 42
assert calculate(parse("INT(\"42.9\")")).value == 42
assert calculate(parse("INT(\"-42.9\")")).value == -42
assert calculate(parse("IF(1=2,99,88)")).value == 88
assert calculate(parse("IF(2=2,99,88)")).value == 99
try:
    assert calculate(parse("5 / (2-1-1)"))
    assert False
except ZeroDivisionException as ex:
    pass
try:
    assert calculate(parse("5 % (2-1-1)"))
    assert False
except ZeroDivisionException as ex:
    pass


def main():
    st = parse(" ".join(sys.argv[1:]))
    print(st)
    print(calculate(st))


if __name__ == "__main__":
    main()
