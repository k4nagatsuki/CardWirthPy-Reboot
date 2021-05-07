#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import re
import decimal
import fnmatch

import cw

import typing
from typing import Callable, List, Optional, Sequence, Tuple, Union


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
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: str,
                 line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class ArgumentIsNotStringException(ComputeException):
    """関数の引数が文字列でない。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: str,
                 line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class ArgumentIsNotBooleanException(ComputeException):
    """関数の引数が真偽値でない。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: str,
                 line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class ArgumentIsNotListException(ComputeException):
    """関数の引数がリストでない。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: str,
                 line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value


class ArgumentIsNotStructureException(ComputeException):
    """関数の引数が構造体でない。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: str, struct_name: str,
                 line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value
        self.struct_name = struct_name


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


class ListIndexOutOfRangeException(ComputeException):
    """リストにn番目の要素は存在しない。"""
    def __init__(self, msg: str, func_name: str, arg_index: int, arg_value: str, n: int, list_len: int, line: int,
                 pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.func_name = func_name
        self.arg_index = arg_index
        self.arg_value = arg_value
        self.n = n
        self.list_len = list_len


class ExprPermissionError(ComputeException):
    """アクセスできないメンバにアクセスしようとした。"""
    def __init__(self, msg: str, info: "StructureInfo", m: Optional["StructureMember"], line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.info = info
        self.m = m


class DifferentStructureException(ComputeException):
    """構造体の名前が一致しない。"""
    def __init__(self, msg: str, lhs_name: str, rhs_name: str, line: int, pos: int) -> None:
        ComputeException.__init__(self, msg, line, pos)
        self.lhs_name = lhs_name
        self.rhs_name = rhs_name


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
                 args: List[List[Union["ValueType", "Function", "UnaryOperator", "Operator", "Symbol"]]]) -> None:
        self.name = name.lower()
        self.line = line
        self.pos = pos
        self.args = args

    def call(self, option: "CalcOption") -> "ValueType":
        args = []
        for arg in self.args:
            class F(object):
                def __init__(self, arg: List[Union[ValueType, Function, UnaryOperator, Operator, Symbol]],
                             option: CalcOption) -> None:
                    self.arg = arg
                    self.option = option

                def eval_arg(self) -> ValueType:
                    return calculate(self.arg, self.option)

            args.append(F(arg, option).eval_arg)
        name = self.name
        if name in _functions:
            return _functions[name](args, option, self.line, self.pos)
        elif name in _structures:
            return _create_structure(_structures[name], args, option, self.line, self.pos)
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

    def call(self, rhs: Union["ValueType", "Symbol"]) -> "ValueType":
        o = self.operator
        if isinstance(rhs, Symbol):
            raise SemanticsException("Unknown symbol: %s" % rhs.symbol, rhs.line, rhs.pos)
        if o == '+':
            if not isinstance(rhs, DecimalValue):
                raise SemanticsException("value [%s] is not number." % rhs.to_str(), rhs.line, rhs.pos)
            return DecimalValue(rhs.value, self.line, self.pos)
        elif o == '-':
            if not isinstance(rhs, DecimalValue):
                raise SemanticsException("value [%s] is not number." % rhs.to_str(), rhs.line, rhs.pos)
            return DecimalValue(-rhs.value, self.line, self.pos)
        elif o.lower() == "not":
            if not isinstance(rhs, BooleanValue):
                raise SemanticsException("value [%s] is not boolean." % rhs.to_str(), rhs.line, rhs.pos)
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

    @staticmethod
    def chk_num(lhs: "ValueType", rhs: "ValueType") -> Tuple[decimal.Decimal, decimal.Decimal]:
        if not isinstance(lhs, DecimalValue):
            raise SemanticsException("lhs [%s] is not number." % lhs.to_str(), lhs.line, lhs.pos)
        if not isinstance(rhs, DecimalValue):
            raise SemanticsException("rhs [%s] is not number." % rhs.to_str(), rhs.line, rhs.pos)
        assert isinstance(lhs.value, decimal.Decimal)
        assert isinstance(rhs.value, decimal.Decimal)
        return lhs.value, rhs.value

    @staticmethod
    def chk_str(lhs: "ValueType", rhs: "ValueType") -> Tuple[str, str]:
        if not isinstance(lhs, StringValue):
            raise SemanticsException("lhs [%s] is not string." % lhs.to_str(), lhs.line, lhs.pos)
        if not isinstance(rhs, StringValue):
            raise SemanticsException("rhs [%s] is not string." % rhs.to_str(), rhs.line, rhs.pos)
        assert isinstance(lhs.value, str)
        assert isinstance(rhs.value, str)
        return lhs.value, rhs.value

    @staticmethod
    def chk_bool(lhs: "ValueType", rhs: "ValueType") -> Tuple[bool, bool]:
        if not isinstance(lhs, BooleanValue):
            raise SemanticsException("lhs [%s] is not boolean." % lhs.to_str(), lhs.line, lhs.pos)
        if not isinstance(rhs, BooleanValue):
            raise SemanticsException("rhs [%s] is not boolean." % rhs.to_str(), rhs.line, rhs.pos)
        assert isinstance(lhs.value, bool)
        assert isinstance(rhs.value, bool)
        return lhs.value, rhs.value

    @staticmethod
    def chk_list(val: "ValueType") -> "ListValue":
        if not isinstance(val, ListValue):
            raise SemanticsException("rhs [%s] is not list." % val.to_str(), val.line, val.pos)
        return val

    @staticmethod
    def chk_struct(val: "ValueType") -> "StructureValue":
        if not isinstance(val, StructureValue):
            raise SemanticsException("rhs [%s] is not structure." % (val.to_str()), val.line, val.pos)
        return val

    @staticmethod
    def chk_structmembername(val: Union["ValueType", "Symbol"]) -> "Symbol":
        if not isinstance(val, Symbol):
            raise SemanticsException("rhs [%s] is not struct member name." % (val.to_str()), val.line, val.pos)
        return val

    @staticmethod
    def equals(lhs: "ValueType", rhs: "ValueType", o: str, in_list: bool) -> bool:
        if isinstance(lhs, ListValue):
            lhs_list = lhs
            if not in_list:
                rhs_list = Operator.chk_list(rhs)
            elif isinstance(rhs, ListValue):
                rhs_list = rhs
            else:
                return o == "<>"
            for i in range(min(len(lhs_list.value), len(rhs_list.value))):
                b = Operator.equals(lhs_list.eval(i), rhs_list.eval(i), "=", True)
                if not b:
                    if o == "<>":
                        b = not b
                    return b
            b = len(lhs_list.value) == len(rhs_list.value)
            if o == "<>":
                b = not b
            return b
        elif isinstance(lhs, StructureValue):
            lhs_struct = lhs
            if not in_list:
                rhs_struct = Operator.chk_struct(rhs)
            elif isinstance(rhs, StructureValue):
                rhs_struct = rhs
            else:
                return o == "<>"
            if lhs_struct.name != rhs_struct.name:
                if in_list:
                    return o == "<>"
                else:
                    raise DifferentStructureException("different structure %s:%s." % (lhs_struct.name,
                                                                                      rhs_struct.name),
                                                      lhs_struct.name, rhs_struct.name, rhs_struct.line,
                                                      rhs_struct.pos)
            for i in range(min(len(lhs_struct.value), len(rhs_struct.value))):
                b = Operator.equals(lhs_struct.eval(i), rhs_struct.eval(i), "=", True)
                if not b:
                    if o == "<>":
                        b = not b
                    return b
            return o == "="

        if not in_list and (isinstance(lhs, StringValue) or isinstance(rhs, StringValue)):
            r = lhs.to_str() == rhs.to_str()
        elif isinstance(lhs, StringValue):
            if in_list and not isinstance(rhs, StringValue):
                return o == "<>"
            lhs_str, rhs_str = Operator.chk_str(lhs, rhs)
            r = lhs_str == rhs_str
        elif isinstance(lhs, BooleanValue):
            if in_list and not isinstance(rhs, BooleanValue):
                return o == "<>"
            lhs_bool, rhs_bool = Operator.chk_bool(lhs, rhs)
            r = lhs_bool == rhs_bool
        else:
            if in_list and not isinstance(rhs, DecimalValue):
                return o == "<>"
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            r = lhs_int == rhs_int
        if o == "<>":
            r = not r
        return r

    def call(self, lhs: Union["ValueType", "Symbol"], rhs: Union["ValueType", "Symbol"],
             option: "CalcOption", o: Optional[str] = None) -> "ValueType":
        if o is None:
            o = self.operator

        if isinstance(lhs, Symbol):
            raise SemanticsException("Unknown symbol: %s" % lhs.symbol, lhs.line, lhs.pos)
        if o != '.' and isinstance(rhs, Symbol):
            raise SemanticsException("Unknown symbol: %s" % rhs.symbol, rhs.line, rhs.pos)

        if o == '.':
            lhs_struct = Operator.chk_struct(lhs)
            if lhs_struct.name not in _structures:
                raise SemanticsException("structure %s is not found." % lhs_struct.name, rhs.line, rhs.pos)
            struct_info = _structures[lhs_struct.name]
            rhs_symbol = Operator.chk_structmembername(rhs)
            mindex = struct_info.index_of(rhs_symbol.symbol)
            m = struct_info.members[mindex]
            if not m.is_public and option.evaltype != "Test":
                raise ExprPermissionError("Structure member %s.%s is not accesible." % (struct_info.name.upper(),
                                                                                        m.name.upper()),
                                          struct_info, m, self.line, self.pos)
            if mindex == -1:
                raise SemanticsException("structure %s has not been %s." % (lhs_struct.name, rhs_symbol.symbol),
                                         rhs.line, rhs.pos)
            return lhs_struct.eval(mindex)
        assert not isinstance(rhs, Symbol)
        if o == '+':
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            return DecimalValue(lhs_int + rhs_int, self.line, self.pos)
        elif o == '-':
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            return DecimalValue(lhs_int - rhs_int, self.line, self.pos)
        elif o == '*':
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            return DecimalValue(lhs_int * rhs_int, self.line, self.pos)
        elif o == '/':
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            if rhs_int == 0:
                raise ZeroDivisionException("Division by zero.", self.line, self.pos)
            return DecimalValue(lhs_int / rhs_int, self.line, self.pos)
        elif o == '%':
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            if rhs_int == 0:
                raise ZeroDivisionException("Division by zero.", self.line, self.pos)
            return DecimalValue(lhs_int % rhs_int, self.line, self.pos)
        elif o == '~':
            if isinstance(lhs, ListValue):
                if isinstance(rhs, ListValue):
                    return ListValue(lhs.value + rhs.value, self.line, self.pos)
                else:
                    return ListValue(lhs.value + [rhs], self.line, self.pos)
            elif isinstance(rhs, ListValue):
                lhs2: List[Union[ValueType, Callable[[], ValueType]]] = [lhs]
                return ListValue(lhs2 + rhs.value, self.line, self.pos)
            return StringValue(lhs.to_str() + rhs.to_str(), self.line, self.pos)
        elif o == "<=":
            if isinstance(lhs, ListValue):
                lhs_list = lhs
                rhs_list = Operator.chk_list(rhs)
                for i in range(min(len(lhs_list.value), len(rhs_list.value))):
                    b = self.call(lhs_list.eval(i), rhs_list.eval(i), option, "<")
                    assert isinstance(b, BooleanValue)
                    if b.value:
                        return b
                return BooleanValue(len(lhs_list.value) <= len(rhs_list.value), self.line, self.pos)
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            return BooleanValue(lhs_int <= rhs_int, self.line, self.pos)
        elif o == ">=":
            if isinstance(lhs, ListValue):
                lhs_list = lhs
                rhs_list = Operator.chk_list(rhs)
                for i in range(min(len(lhs_list.value), len(rhs_list.value))):
                    b = self.call(lhs_list.eval(i), rhs_list.eval(i), option, ">")
                    assert isinstance(b, BooleanValue)
                    if b.value:
                        return b
                return BooleanValue(len(lhs_list.value) >= len(rhs_list.value), self.line, self.pos)
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            return BooleanValue(lhs_int >= rhs_int, self.line, self.pos)
        elif o == "<":
            if isinstance(lhs, ListValue):
                lhs_list = lhs
                rhs_list = Operator.chk_list(rhs)
                for i in range(min(len(lhs_list.value), len(rhs_list.value))):
                    b = self.call(lhs_list.eval(i), rhs_list.eval(i), option, "<")
                    assert isinstance(b, BooleanValue)
                    if b.value:
                        return b
                return BooleanValue(len(lhs_list.value) < len(rhs_list.value), self.line, self.pos)
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            return BooleanValue(lhs_int < rhs_int, self.line, self.pos)
        elif o == ">":
            if isinstance(lhs, ListValue):
                lhs_list = lhs
                rhs_list = Operator.chk_list(rhs)
                for i in range(min(len(lhs_list.value), len(rhs_list.value))):
                    b = self.call(lhs_list.eval(i), rhs_list.eval(i), option, ">")
                    assert isinstance(b, BooleanValue)
                    if b.value:
                        return b
                return BooleanValue(len(lhs_list.value) > len(rhs_list.value), self.line, self.pos)
            lhs_int, rhs_int = Operator.chk_num(lhs, rhs)
            return BooleanValue(lhs_int > rhs_int, self.line, self.pos)
        elif o in ("=", "<>"):
            r = Operator.equals(lhs, rhs, o, False)
            return BooleanValue(r, self.line, self.pos)
        elif o.lower() == "and":
            lhs_bool, rhs_bool = Operator.chk_bool(lhs, rhs)
            return BooleanValue(lhs_bool and rhs_bool, self.line, self.pos)
        elif o.lower() == "or":
            lhs_bool, rhs_bool = Operator.chk_bool(lhs, rhs)
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
    line: int
    pos: int

    def to_value_obj(self) -> "ValueType":
        return self

    def to_str(self) -> str:
        return ""


class DecimalValue(ValueType):
    """数値トークン。"""
    value: decimal.Decimal

    def __init__(self, s: Union[str, decimal.Decimal, int, float], line: int, pos: int) -> None:
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


class ListValue(ValueType):
    """リスト。"""
    value: List[Union[ValueType, Callable[[], ValueType]]]

    def __init__(self, s: List[Union[ValueType, Callable[[], ValueType]]], line: int, pos: int) -> None:
        self.value = s
        self.line = line
        self.pos = pos

    def eval(self, i: int) -> ValueType:
        val = self.value[i]
        if callable(val):
            val2 = val()
            self.value[i] = val2
            return val2
        else:
            return val

    def to_str(self) -> str:
        def to_str(i: int) -> str:
            v = self.eval(i)
            if isinstance(v, StringValue):
                return "\"" + v.value.replace("\"", "\"\"") + "\""
            else:
                return v.to_str()

        return "LIST(" + ", ".join(map(to_str, range(len(self.value)))) + ")"

    def __repr__(self) -> str:
        return self.to_str()


assert ListValue([ListValue([ListValue([StringValue("STR", 0, 0)], 0, 0)], 0, 0)], 0, 0).to_str() ==\
    "LIST(LIST(LIST(\"STR\")))"


class StructureMember(object):
    """構造体メンバ定義。"""
    def __init__(self, name: str, is_public: bool, defvalue: "cw.data.VariantValueType", type_check: bool,
                 vtype: str = "", min_value: Optional[decimal.Decimal] = None, struct_name: str = "") -> None:
        self.name = name  # 構造体メンバ名
        self.is_public = is_public  # ユーザがアクセス可能なメンバか
        self.defvalue = defvalue  # 未指定時の値
        self.type_check = type_check  # 型チェックを行うか
        self.vtype = vtype  # 型
        self.min_value = min_value  # 数値型の時の下限値。下限がない場合はNone
        self.struct_name = struct_name  # 構造体型の時の構造体名


class StructureInfo(object):
    """構造体定義。"""
    def __init__(self, name: str, is_public: bool, members: Sequence[StructureMember],
                 required_member_num: int) -> None:
        self.name = name  # 構造体名
        self.is_public = is_public  # ユーザが作成可能な構造体か
        self.members = members  # メンバ定義
        self.required_member_num = required_member_num  # 生成時に必ず値を指定しなければならないメンバの数
        self._index_table = {}
        for i, mem in enumerate(members):
            self._index_table[mem.name] = i

    def index_of(self, name: str) -> int:
        """
        メンバのインデックスを返す。
        指定された名前のメンバが存在しない場合は-1を返す。
        """
        return self._index_table.get(name.lower(), -1)


_structures = {
    "cardinfo": StructureInfo("cardinfo", False, [
        StructureMember("castindex", False, decimal.Decimal(0), True, "Number", min_value=decimal.Decimal(-2)),
        StructureMember("cardindex", False, decimal.Decimal(0), True, "Number", min_value=decimal.Decimal(0)),
        StructureMember("actioncardid", False, decimal.Decimal(-2), True, "Number"),
    ], 2)
}


def struct_info(name: str) -> StructureInfo:
    """構造体の情報を返す。"""
    info = _structures.get(name.lower(), None)
    if not info:
        raise Exception("Structure %s has been declared." % name)
    return info


def cut_optionalmembers(name: str,
                        members: Sequence["cw.data.VariantValueType"]) -> Sequence["cw.data.VariantValueType"]:
    """membersの後方にオプショナル項目のデフォルト値があれば削って返す。"""
    info = struct_info(name)
    assert len(info.members) == len(members)
    for i in reversed(range(len(info.members))):
        if i < info.required_member_num or info.members[i].defvalue != members[i]:
            break
        members = members[:i]
    return members


assert cut_optionalmembers("cardinfo", [decimal.Decimal(0), decimal.Decimal(0), decimal.Decimal(-2)]) ==\
                           [decimal.Decimal(0), decimal.Decimal(0)]
assert cut_optionalmembers("cardinfo", [decimal.Decimal(0), decimal.Decimal(0), decimal.Decimal(-2.1)]) ==\
                           [decimal.Decimal(0), decimal.Decimal(0), decimal.Decimal(-2.1)]


def is_valid_structure(name: str, members: Sequence[Tuple[str, "cw.data.VariantValueType"]]) -> bool:
    """構造体名及びメンバ名及び値をチェックし、正しければtrueを返す。"""
    info = _structures.get(name.lower(), None)
    if not info:
        return False
    if len(info.members) < len(members):
        return False
    for i, m in enumerate(info.members):
        if len(members) <= i:
            return info.required_member_num <= i
        if m.name != members[i][0].lower():
            return False
        if m.type_check:
            if m.vtype != cw.data.Variant.value_to_type(members[i][1]):
                return False
            if m.vtype == "Number" and m.min_value is not None:
                num_val = members[i][1]
                assert isinstance(num_val, decimal.Decimal)
                if num_val < m.min_value:
                    return False
            if m.vtype == "Structure":
                struct_val = members[i][1]
                assert isinstance(struct_val, cw.data.StructVal)
                if m.struct_name != struct_val.name:
                    return False
    return True


assert is_valid_structure("cardinfo", [("castindex", decimal.Decimal(4)), ("cardindex", decimal.Decimal(2))])
assert is_valid_structure("CardInfo", [("CastIndex", decimal.Decimal(4)), ("CardIndex", decimal.Decimal(2))])
assert not is_valid_structure("cardinfo_", [("castindex", decimal.Decimal(4)), ("cardindex", decimal.Decimal(2))])
assert not is_valid_structure("cardinfo", [("castindex", decimal.Decimal(4)), ("cardindex", decimal.Decimal(2)),
                                           ("dummy", decimal.Decimal(0))])
assert not is_valid_structure("cardinfo", [("castindex", decimal.Decimal(4))])
assert not is_valid_structure("cardinfo", [("cardindex", decimal.Decimal(4)), ("castindex", decimal.Decimal(2))])
assert not is_valid_structure("cardinfo", [("castindex", ""), ("cardindex", decimal.Decimal(2))])
assert not is_valid_structure("cardinfo", [("castindex", decimal.Decimal(4)), ("cardindex", False)])
assert is_valid_structure("cardinfo", [("castindex", decimal.Decimal(-2)), ("cardindex", decimal.Decimal(0))])
assert not is_valid_structure("cardinfo", [("castindex", decimal.Decimal(-2.1)), ("cardindex", decimal.Decimal(2))])
assert not is_valid_structure("cardinfo", [("castindex", decimal.Decimal(4)), ("cardindex", decimal.Decimal(-0.1))])


class StructureValue(ValueType):
    """構造体。"""
    name: str
    value: List[Union[ValueType, Callable[[], ValueType]]]

    def __init__(self, name: str, s: List[Union[ValueType, Callable[[], ValueType]]], line: int, pos: int) -> None:
        self.name = name.lower()
        self.value = s
        info = _structures[self.name]
        for m in info.members[len(s):]:
            self.value.append(_variantvalue_to_valuetype(m.defvalue, line, pos))
        self.line = line
        self.pos = pos

    def eval(self, i: int) -> ValueType:
        val = self.value[i]
        if callable(val):
            val2 = val()

            m = _structures[self.name].members[i]
            if m.type_check:
                uname = self.name
                if m.vtype == "Number":
                    if m.min_value is not None:
                        _chk_minvalue(val2, uname, i, m.min_value)
                    else:
                        _chk_decimal(val2, uname, i)
                elif m.vtype == "String":
                    _chk_string(val2, uname, i)
                elif m.vtype == "Boolean":
                    _chk_boolean(val2, uname, i)
                elif m.vtype == "List":
                    _chk_list(val2, uname, i)
                elif m.vtype == "Structure":
                    _chk_structure(val2, uname, i, m.struct_name)
                else:
                    assert False

            self.value[i] = val2
            return val2
        else:
            return val

    def to_str(self) -> str:
        return cw.data.Variant.value_to_str(to_variantvalue(self))

    def __repr__(self) -> str:
        return self.to_str()


class Symbol(object):
    """その他シンボル。"""
    def __init__(self, symbol: str, line: int, pos: int) -> None:
        self.symbol = symbol
        self.line = line
        self.pos = pos

    def to_value_obj(self) -> ValueType:
        ls = self.symbol.lower()
        if ls in _symbols:
            return _variantvalue_to_valuetype(_symbols[ls], self.line, self.pos)
        else:
            raise SemanticsException("Unknown symbol: %s" % self.symbol.upper(), self.line, self.pos)


def parse(s: str) -> List[Union[ValueType, Function, UnaryOperator, Operator, Symbol]]:
    """文字列sを式として解析し、スタックを生成する。"""
    tokens = []
    bpos = 0
    bm: Optional[re.Match[str]] = None
    line = 1
    pos = 1
    reg = "[0-9]+(\\.[0-9]+)?|[a-z_][a-z_0-9]*|[\\+\\-\\*\\/\\%\\~\\.]|[\\(\\)]|,|@?\"([^\"]|\"\")*\"|or|and|"\
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
                        i: int) -> Tuple[int, List[List[Union[ValueType, Function, UnaryOperator, Operator, Symbol]]]]:
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
                        i: int) -> Tuple[int, List[Union[ValueType, Function, UnaryOperator, Operator, Symbol]]]:
        num: List[Union[ValueType, Function, UnaryOperator, Operator, Symbol]] = []
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
            elif t == ".":
                if isop:
                    raise SemanticsException("Need a symbol or number here.", line, pos)
                # 構造体メンバアクセス
                oplevel = 100
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
                if i + 1 < len(tokens) and tokens[i + 1].token == "(":
                    # 関数呼び出し
                    i, args = parse_arguments(tokens, i)
                    num.append(Function(t, line, pos, args))
                else:
                    # シンボル・構造体メンバ名
                    num.append(Symbol(t, line, pos))
                    i += 1
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


class CalcOption(object):
    def __init__(self, evaltype: str, is_differentscenario: bool) -> None:
        self.evaltype = evaltype
        self.is_differentscenario = is_differentscenario


def calculate(st: List[Union[ValueType, Function, UnaryOperator, Operator, Symbol]],
              option: CalcOption = CalcOption("Event", False)) -> ValueType:
    """スタックstの式を実行する。"""
    op: List[Union[ValueType, Symbol]] = []
    for t in st:
        if isinstance(t, Function):
            # 関数呼び出し
            v: Union[ValueType, Symbol] = t.call(option)
        elif isinstance(t, UnaryOperator):
            # 単項演算子
            if not op:
                raise SemanticsException("Invalid semantics.", t.line, t.pos)
            rhs = op.pop()
            v = t.call(rhs.to_value_obj())
        elif isinstance(t, Operator):
            # 二項演算子
            if not op:
                raise SemanticsException("Invalid semantics.", t.line, t.pos)
            rhs = op.pop()
            if not op:
                raise SemanticsException("Invalid semantics.", t.line, t.pos)
            lhs = op.pop()
            lhs = lhs.to_value_obj()
            if t.operator != ".":
                rhs = rhs.to_value_obj()
            v = t.call(lhs, rhs, option)
        else:
            # 数値・文字列・真偽値・シンボル
            v = t
        op.append(v)
    if not op:
        raise SemanticsException("Invalid semantics.", 0, 0)
    t = op.pop(-1)
    return t.to_value_obj()


def eval_expr(st: List[Union[ValueType, Function, UnaryOperator, Operator, Symbol]],
              option: CalcOption) -> cw.data.Variant:
    val = calculate(st, option)
    return cw.data.Variant(None, None, to_variantvalue(val), "", "")


def to_variantvalue(val: ValueType) -> cw.data.VariantValueType:
    if isinstance(val, ListValue):
        # BUG: error: Cannot resolve name "VariantValueType" (possible cyclic definition) (mypy 0.790)
        # return [to_variantvalue(val.eval(i)) for i in range(len(val.value))]
        return typing.cast(cw.data.VariantValueType, [to_variantvalue(val.eval(i)) for i in range(len(val.value))])
    elif isinstance(val, StructureValue):
        members = [to_variantvalue(val.eval(i)) for i in range(len(val.value))]
        return cw.data.StructVal(val.name, members)
    else:
        assert isinstance(val, (StringValue, DecimalValue, BooleanValue))
        return val.value


def _chk_diffsc(option: CalcOption, line: int, pos: int) -> None:
    if option.is_differentscenario:
        raise DifferentScenarioException("Read a variable at different scenario.", line, pos)


def _chk_argscount(args: List[Callable[[], ValueType]], n: int, func_name: str, line: int, pos: int) -> None:
    if len(args) != n:
        raise ArgumentsCountException("Invalid arguments count: %s != %s" % (n, len(args)), func_name, line, pos)


def _chk_argscount2(args: List[Callable[[], ValueType]], n1: int, n2: int, func_name: str, line: int, pos: int) -> None:
    if n1 == n2:
        return _chk_argscount(args, n1, func_name, line, pos)
    if not len(args) in (n1, n2):
        raise ArgumentsCountException("Invalid arguments count: %s-%s != %s" % (n1, n2, len(args)), func_name, line,
                                      pos)


def _chk_decimal(arg: ValueType, func_name: str, arg_index: int) -> decimal.Decimal:
    """argがDecimalValueか調べる。"""
    if isinstance(arg, DecimalValue):
        assert isinstance(arg.value, decimal.Decimal)
        return arg.value
    else:
        raise ArgumentIsNotDecimalException("%s is not Decimal." % arg.to_str(), func_name, arg_index, arg.to_str(),
                                            arg.line, arg.pos)


def _chk_minvalue(arg: ValueType, func_name: str, arg_index: int,
                  minvalue: Union[int, decimal.Decimal] = 0) -> decimal.Decimal:
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
        raise ArgumentIsNotStringException("%s is not String." % arg.to_str(), func_name, arg_index, arg.to_str(),
                                           arg.line, arg.pos)


def _chk_boolean(arg: ValueType, func_name: str, arg_index: int) -> bool:
    """argがBooleanValueか調べる。"""
    if isinstance(arg, BooleanValue):
        assert isinstance(arg.value, bool)
        return arg.value
    else:
        raise ArgumentIsNotBooleanException("%s is not Boolean." % arg.to_str(), func_name, arg_index, arg.to_str(),
                                            arg.line, arg.pos)


def _chk_list(arg: ValueType, func_name: str, arg_index: int) -> ListValue:
    """argがListValueか調べる。"""
    if isinstance(arg, ListValue):
        assert isinstance(arg.value, list)
        return arg
    else:
        raise ArgumentIsNotListException("%s is not List." % arg.to_str(), func_name, arg_index, arg.to_str(), arg.line,
                                         arg.pos)


def _chk_structure(arg: ValueType, func_name: str, arg_index: int, struct_name: str) -> StructureValue:
    """argがStructureValueか調べる。"""
    if isinstance(arg, StructureValue) and arg.name == struct_name:
        return arg
    else:
        raise ArgumentIsNotStructureException("%s is not Structure." % arg.to_str(), func_name, arg_index,
                                              arg.to_str(), struct_name, arg.line, arg.pos)


def _is_alldecimal(args: List[ValueType], func_name: str) -> bool:
    """argsが全てDecimalValueで構成されているか検査する。"""
    for i, arg in enumerate(args):
        _chk_decimal(arg, func_name, i)
    return True


def _all_eval(args: List[Callable[[], ValueType]]) -> List[ValueType]:
    return [arg() for arg in args]


def _func_max(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """引数中の最大の値を返す。"""
    args_r = _all_eval(args)
    if len(args_r) and _is_alldecimal(args_r, "MAX"):
        def val_int(a: ValueType) -> decimal.Decimal:
            assert isinstance(a, DecimalValue)
            return a.value
        val = max(*map(val_int, args_r)) if 1 < len(args_r) else val_int(args_r[0])
        assert isinstance(val, decimal.Decimal)
        return DecimalValue(val, line, pos)
    raise ArgumentsCountException("No argments of max.", "MAX", line, pos)


def _func_min(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """引数中の最小の値を返す。"""
    args_r = _all_eval(args)
    if len(args_r) and _is_alldecimal(args_r, "MIN"):
        def val_int(a: ValueType) -> decimal.Decimal:
            assert isinstance(a, DecimalValue)
            return a.value
        val = min(*map(val_int, args_r)) if 1 < len(args_r) else val_int(args_r[0])
        assert isinstance(val, decimal.Decimal)
        return DecimalValue(val, line, pos)
    raise ArgumentsCountException("No argments of min.", "MIN", line, pos)


def _func_len(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """文字列の文字数を返す。"""
    _chk_argscount(args, 1, "LEN", line, pos)
    args_r = _all_eval(args)
    a = args_r[0]
    return DecimalValue(len(_chk_string(a, "LEN", 0)), line, pos)


def _func_find(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
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


def _func_left(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """文字列の左側を取り出す。"""
    _chk_argscount(args, 2, "LEFT", line, pos)
    args_r = _all_eval(args)
    s = args_r[0]
    n = args_r[1]
    a = _chk_string(s, "LEFT", 0)
    v = min(int(_chk_minvalue(n, "LEFT", 1)), len(a))
    return StringValue(a[:int(v)], line, pos)


def _func_right(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """文字列の右側を取り出す。"""
    _chk_argscount(args, 2, "RIGHT", line, pos)
    args_r = _all_eval(args)
    s = args_r[0]
    n = args_r[1]
    a = _chk_string(s, "RIGHT", 0)
    v = len(a) - min(int(_chk_minvalue(n, "RIGHT", 1)), len(a))
    return StringValue(a[int(v):], line, pos)


def _func_mid(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
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


def _func_str(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """引数を文字列に変換する。"""
    _chk_argscount(args, 1, "STR", line, pos)
    args_r = _all_eval(args)
    return StringValue(args_r[0].to_str(), line, pos)


_NUM_REG = re.compile("\\A\\s*-?([0-9]+(\\.[0-9]*)?|([0-9]*\\.)?[0-9]+)\\s*\\Z")


def _func_value(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
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
            raise InvalidArgumentException("Invalid argument: %s" % a.to_str(), "VALUE", 0, a.to_str(), a.line, a.pos)
        try:
            value = decimal.Decimal(a.value)
        except Exception:
            raise InvalidArgumentException("Invalid argument: %s" % a.to_str(), "VALUE", 0, a.to_str(), a.line, a.pos)
    else:
        raise InvalidArgumentException("Invalid argument: %s" % a.to_str(), "VALUE", 0, a.to_str(), a.line, a.pos)
    return DecimalValue(value, line, pos)


def _func_int(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
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
            raise InvalidArgumentException("Invalid argument: %s" % a.to_str(), "INT", 0, a.to_str(), a.line, a.pos)
    else:
        raise InvalidArgumentException("Invalid argument: %s" % a.to_str(), "INT", 0, a.to_str(), a.line, a.pos)
    return DecimalValue(value.to_integral_exact(decimal.ROUND_DOWN), line, pos)


def _func_if(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> ValueType:
    """args[0]がTrueであればargs[1]を、そうでなければargs[2]を返す。"""
    _chk_argscount(args, 3, "IF", line, pos)
    a = args[0]()
    a_bool = _chk_boolean(a, "IF", 0)
    t = args[1]
    f = args[2]
    return t() if a_bool else f()


def _func_var(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> ValueType:
    """汎用変数の値を読む。"""
    _chk_argscount(args, 1, "VAR", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "VAR", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.variants:
        variant = event.variants[path]
    elif path in cw.cwpy.sdata.variants:
        _chk_diffsc(option, line, pos)
        variant = cw.cwpy.sdata.variants[path]
    else:
        raise VariantNotFoundException("Variant \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    if variant.type == "Boolean":
        assert isinstance(variant.value, bool)
        return BooleanValue(variant.value, line, pos)
    elif variant.type == "Number":
        assert isinstance(variant.value, decimal.Decimal)
        return DecimalValue(variant.value, line, pos)
    elif variant.type == "String":
        assert isinstance(variant.value, str)
        return StringValue(variant.value, line, pos)
    elif variant.type == "List":
        assert isinstance(variant.value, list)
        return _variantvalue_to_valuetype(variant.value, line, pos)
    else:
        assert variant.type == "Structure"
        assert isinstance(variant.value, cw.data.StructVal)
        return _variantvalue_to_valuetype(variant.value, line, pos)


def _variantvalue_to_valuetype(val: cw.data.VariantValueType, line: int, pos: int) -> ValueType:
    if isinstance(val, str):
        return StringValue(val, line, pos)
    elif isinstance(val, decimal.Decimal):
        return DecimalValue(val, line, pos)
    elif isinstance(val, bool):
        return BooleanValue(val, line, pos)
    elif isinstance(val, cw.data.StructVal):
        return StructureValue(val.name, [_variantvalue_to_valuetype(val, line, pos) for val in val.members], line, pos)
    else:
        return ListValue([_variantvalue_to_valuetype(val, line, pos) for val in val], line, pos)


def _func_flagvalue(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> BooleanValue:
    """フラグの値を読む。"""
    _chk_argscount(args, 1, "FLAGVALUE", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "FLAGVALUE", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.flags:
        flag = event.flags[path]
    elif path in cw.cwpy.sdata.flags:
        _chk_diffsc(option, line, pos)
        flag = cw.cwpy.sdata.flags[path]
    else:
        raise FlagNotFoundException("Flag \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    return BooleanValue(flag.value, line, pos)


def _func_flagtext(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """フラグの値の文字列を読む。"""
    _chk_argscount2(args, 1, 2, "FLAGTEXT", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "FLAGTEXT", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.flags:
        flag = event.flags[path]
    elif path in cw.cwpy.sdata.flags:
        _chk_diffsc(option, line, pos)
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


def _func_stepvalue(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """ステップの値を読む。"""
    _chk_argscount(args, 1, "STEPVALUE", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "STEPVALUE", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.steps:
        step = event.steps[path]
    elif path in cw.cwpy.sdata.steps:
        _chk_diffsc(option, line, pos)
        step = cw.cwpy.sdata.steps[path]
    else:
        raise StepNotFoundException("Step \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    return DecimalValue(decimal.Decimal(step.value), line, pos)


def _func_steptext(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """ステップの値の文字列を読む。"""
    _chk_argscount2(args, 1, 2, "STEPTEXT", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "STEPTEXT", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.steps:
        step = event.steps[path]
    elif path in cw.cwpy.sdata.steps:
        _chk_diffsc(option, line, pos)
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


def _func_stepmax(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """ステップの最大値を取得する。"""
    _chk_argscount(args, 1, "STEPMAX", line, pos)
    args_r = _all_eval(args)
    path = _chk_string(args_r[0], "STEPMAX", 0)

    event = cw.cwpy.event.get_nowrunningevent()
    if event and path in event.steps:
        step = event.steps[path]
    elif path in cw.cwpy.sdata.steps:
        _chk_diffsc(option, line, pos)
        step = cw.cwpy.sdata.steps[path]
    else:
        raise StepNotFoundException("Step \"%s\" is not found.", path, args_r[0].line, args_r[0].pos)

    return DecimalValue(decimal.Decimal(len(step.valuenames)-1), line, pos)


def _func_dice(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
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


def _ccard_index(ccard: cw.character.Character) -> int:
    if isinstance(ccard, cw.sprite.card.PlayerCard):
        pcards = cw.cwpy.get_pcards()
        return pcards.index(ccard) + 1
    elif isinstance(ccard, cw.sprite.card.EnemyCard):
        pcards_len = len(cw.cwpy.get_pcards())
        ecards = cw.cwpy.get_ecards()
        return ecards.index(ccard) + 1 + pcards_len
    elif isinstance(ccard, cw.sprite.card.FriendCard):
        pcards_len = len(cw.cwpy.get_pcards())
        ecards_len = len(cw.cwpy.get_ecards())
        fcards = cw.cwpy.get_fcards()
        return fcards.index(ccard) + 1 + pcards_len + ecards_len
    else:
        assert False


def _func_selected(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """選択メンバのキャラクター番号を数値(1～)で返す。"""
    _chk_argscount(args, 0, "SELECTED", line, pos)
    if cw.cwpy.event.has_selectedmember():
        try:
            ccard = cw.cwpy.event.get_selectedmember()
            assert ccard is not None
            n = _ccard_index(ccard)
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


def _func_casttype(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
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


def _func_castname(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """キャラクター番号からキャラクターの名前を返す。"""
    _chk_argscount(args, 1, "CASTNAME", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "CASTNAME")
    if ccard:
        return StringValue(ccard.get_showingname(), line, pos)
    else:
        return StringValue("", line, pos)


def _func_findcoupon(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
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


def _func_coupontext(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
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


def _func_findgossip(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
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


def _func_gossiptext(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """ゴシップ名を返す。"""
    _chk_argscount(args, 1, "GOSSIPTEXT", line, pos)
    args_r = _all_eval(args)
    index = int(_chk_minvalue(args_r[0], "GOSSIPTEXT", 0)) - 1
    if cw.cwpy.ydata is None or index < 0 or cw.cwpy.ydata.gossips_len() <= index:
        return StringValue("", line, pos)
    return StringValue(cw.cwpy.ydata.get_gossip_at(index), line, pos)


def _func_partyname(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """パーティ名を返す。"""
    _chk_argscount(args, 0, "PARTYNAME", line, pos)
    if cw.cwpy.ydata is None or cw.cwpy.ydata.party is None:
        return StringValue("", line, pos)
    return StringValue(cw.cwpy.ydata.party.get_showingname(), line, pos)


def _func_list(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> ListValue:
    """リストを生成する。"""
    args2: List[Union[ValueType, Callable[[], ValueType]]] = []
    args2.extend(args)
    return ListValue(args2, line, pos)


def _func_at(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> ValueType:
    """リストの要素を取り出す。"""
    _chk_argscount(args, 2, "AT", line, pos)
    args_r = _all_eval(args)
    a = _chk_list(args_r[0], "AT", 0)
    index = int(_chk_minvalue(args_r[1], "AT", 1, 1)) - 1
    if len(a.value) <= index:
        raise ListIndexOutOfRangeException("List index is out of range.", "AT", 1, args_r[1].to_str(), index + 1,
                                           len(a.value), args_r[1].line, args_r[1].pos)
    return a.eval(index)


def _func_llen(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """リストの長さを返す。"""
    _chk_argscount(args, 1, "LLEN", line, pos)
    args_r = _all_eval(args)
    a = _chk_list(args_r[0], "LLEN", 0)
    return DecimalValue(len(a.value), line, pos)


def _func_lfind(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """リスト内を検索する。"""
    _chk_argscount2(args, 2, 3, "LFIND", line, pos)
    args_r = _all_eval(args)
    a = args_r[0]
    t = _chk_list(args_r[1], "LFIND", 1)
    if 2 < len(args_r):
        n = args_r[2]
        start = int(_chk_minvalue(n, "LFIND", 2))
        if start == 0:
            return DecimalValue(0, line, pos)
        start -= 1
        if len(t.value) <= start:
            return DecimalValue(0, line, pos)
    else:
        start = 0
    if not t.value:
        return DecimalValue(0, line, pos)
    for i in range(start, len(t.value)):
        if Operator.equals(a, t.eval(i), "=", True):
            return DecimalValue(i + 1, line, pos)
    return DecimalValue(0, line, pos)


def _func_lleft(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> ListValue:
    """リストの左側を取り出す。"""
    _chk_argscount(args, 2, "LLEFT", line, pos)
    args_r = _all_eval(args)
    s = args_r[0]
    n = args_r[1]
    a = _chk_list(s, "LLEFT", 0)
    v = min(int(_chk_minvalue(n, "LLEFT", 1)), len(a.value))
    return ListValue(a.value[:int(v)], line, pos)


def _func_lright(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> ListValue:
    """リストの右側を取り出す。"""
    _chk_argscount(args, 2, "LRIGHT", line, pos)
    args_r = _all_eval(args)
    s = args_r[0]
    n = args_r[1]
    a = _chk_list(s, "LRIGHT", 0)
    v = len(a.value) - min(int(_chk_minvalue(n, "LRIGHT", 1)), len(a.value))
    return ListValue(a.value[int(v):], line, pos)


def _func_lmid(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> ListValue:
    """リストの[N1-1:N1+N2]の範囲を取り出す。"""
    _chk_argscount2(args, 2, 3, "LMID", line, pos)
    args_r = _all_eval(args)
    s = args_r[0]
    n1 = args_r[1]
    a = _chk_list(s, "LMID", 0).value
    n1value = int(_chk_minvalue(n1, "LMID", 1, 1))
    if len(a)+1 <= n1value:
        a = []
    else:
        v = n1value - 1
        a = a[int(v):]
        if len(args_r) == 3:
            n2 = args_r[2]
            v = min(int(_chk_minvalue(n2, "LMID", 2)), len(a))
            a = a[:int(v)]
    return ListValue(a, line, pos)


def _func_partymoney(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """パーティーの所持金を返す。パーティー非編成時は -1 を返す。"""
    _chk_argscount(args, 0, "PARTYMONEY", line, pos)
    if cw.cwpy.ydata is None or cw.cwpy.ydata.party is None:
        return DecimalValue(-1, line, pos)
    return DecimalValue(cw.cwpy.ydata.party.money, line, pos)


def _func_partynumber(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """パーティーの人数を返す。パーティー非編成時は 0 を返す。"""
    _chk_argscount(args, 0, "PARTYNUMBER", line, pos)
    if cw.cwpy.ydata is None or cw.cwpy.ydata.party is None:
        return DecimalValue(0, line, pos)
    return DecimalValue(len(cw.cwpy.get_pcards()), line, pos)


def _func_yadoname(args: List[Callable[[], ValueType]], option: CalcOption, line: int,
                   pos: int) -> StringValue:
    """拠点名を返す。拠点無しの場合は空文字列を返す。"""
    _chk_argscount(args, 0, "YADONAME", line, pos)
    if cw.cwpy.ydata is None:
        return StringValue("", line, pos)
    return StringValue(cw.cwpy.ydata.get_showingname(), line, pos)


def _func_skintype(args: List[Callable[[], ValueType]], option: CalcOption, line: int,
                   pos: int) -> StringValue:
    """スキン種別の名称を返す。"""
    _chk_argscount(args, 0, "SKINTYPE", line, pos)
    return StringValue(cw.cwpy.setting.skintype, line, pos)


def _func_battleround(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """現バトルのラウンド数を返す。バトル中ではない場合は -1 を返す。"""
    _chk_argscount(args, 0, "BATTLEROUND", line, pos)
    if not cw.cwpy.is_battlestatus():
        return DecimalValue(-1, line, pos)
    assert cw.cwpy.battle
    return DecimalValue(cw.cwpy.battle.round, line, pos)


def _func_castlevel(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """キャラクター番号からキャラクターのレベルを返す。存在しない場合は 0 を返す。"""
    _chk_argscount(args, 1, "CASTLEVEL", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "CASTLEVEL")
    if ccard:
        return DecimalValue(ccard.level, line, pos)
    else:
        return DecimalValue(0, line, pos)


def _func_couponvalue(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """キャラクター番号からキャラクターの所持するクーポン名の点数を返す。
       キャラクターまたはクーポンが存在しない場合は 0 を返す。"""
    _chk_argscount(args, 2, "COUPONVALUE", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "COUPONVALUE")
    coupon_name = _chk_string(args_r[1], "COUPONVALUE", 1)
    if ccard is None:
        return DecimalValue(0, line, pos)
    num = ccard.get_couponvalue(coupon_name, False)
    if num is None:
        return DecimalValue(0, line, pos)
    return DecimalValue(num, line, pos)


def _func_liferatio(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """キャラクター番号からキャラクターのライフ残量を割合で返す。存在しない場合は -1 を返す。"""
    _chk_argscount(args, 1, "LIFERATIO", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "LIFERATIO")
    if ccard:
        return DecimalValue(ccard.life / ccard.maxlife, line, pos)
    else:
        return DecimalValue(-1, line, pos)


def _func_statusvalue(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """キャラクター番号からキャラクターの状態の強度・修正値を返す。存在しない・指定した状態にない場合は 0 を返す。
       強度・修正値を持たない状態にあっては 1 を返す。"""
    _chk_argscount(args, 2, "STATUSVALUE", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "STATUSVALUE")
    status_type = _chk_decimal(args_r[1], "STATUSVALUE", 1)
    if ccard is None:
        return DecimalValue(0, line, pos)

    num = 0
    if status_type == 8:
        num = ccard.poison
    elif status_type == 9:
        num = 1 if ccard.is_sleep() else 0
    elif status_type == 10:
        num = min(ccard.bind, 1)
    elif status_type == 11:
        num = ccard.paralyze
    elif status_type == 12:
        num = 1 if ccard.is_confuse() else 0
    elif status_type == 13:
        num = 1 if ccard.is_overheat() else 0
    elif status_type == 14:
        num = 1 if ccard.is_brave() else 0
    elif status_type == 15:
        num = 1 if ccard.is_panic() else 0
    elif status_type == 16:
        num = min(ccard.silence, 1)
    elif status_type == 17:
        num = min(ccard.faceup, 1)
    elif status_type == 18:
        num = min(ccard.antimagic, 1)
    elif status_type == 19:
        num = ccard.enhance_act if ccard.is_upaction() else 0
    elif status_type == 20:
        num = ccard.enhance_avo if ccard.is_upavoid() else 0
    elif status_type == 21:
        num = ccard.enhance_res if ccard.is_upresist() else 0
    elif status_type == 22:
        num = ccard.enhance_def if ccard.is_updefense() else 0
    elif status_type == 23:
        num = -ccard.enhance_act if ccard.is_downaction() else 0
    elif status_type == 24:
        num = -ccard.enhance_avo if ccard.is_downavoid() else 0
    elif status_type == 25:
        num = -ccard.enhance_res if ccard.is_downresist() else 0
    elif status_type == 26:
        num = -ccard.enhance_def if ccard.is_downdefense() else 0

    if num is None:
        return DecimalValue(0, line, pos)
    return DecimalValue(num, line, pos)


def _func_statusround(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """キャラクター番号からキャラクターの状態の残ラウンド数を返す。存在しない・指定した状態にない場合は 0 を返す。"""
    _chk_argscount(args, 2, "STATUSROUND", line, pos)
    args_r = _all_eval(args)
    ccard = _ccard_from(args_r[0], "STATUSROUND")
    status_type = _chk_decimal(args_r[1], "STATUSROUND", 1)
    if ccard is None:
        return DecimalValue(0, line, pos)

    num = 0
    if status_type == 8:
        num = ccard.poison
    elif status_type == 9:
        num = ccard.mentality_dur if ccard.is_sleep() else 0
    elif status_type == 10:
        num = ccard.bind
    elif status_type == 11:
        num = ccard.paralyze
    elif status_type == 12:
        num = ccard.mentality_dur if ccard.is_confuse() else 0
    elif status_type == 13:
        num = ccard.mentality_dur if ccard.is_overheat() else 0
    elif status_type == 14:
        num = ccard.mentality_dur if ccard.is_brave() else 0
    elif status_type == 15:
        num = ccard.mentality_dur if ccard.is_panic() else 0
    elif status_type == 16:
        num = ccard.silence
    elif status_type == 17:
        num = ccard.faceup
    elif status_type == 18:
        num = ccard.antimagic
    elif status_type == 19:
        num = ccard.enhance_act_dur if ccard.is_upaction() else 0
    elif status_type == 20:
        num = ccard.enhance_avo_dur if ccard.is_upavoid() else 0
    elif status_type == 21:
        num = ccard.enhance_res_dur if ccard.is_upresist() else 0
    elif status_type == 22:
        num = ccard.enhance_def_dur if ccard.is_updefense() else 0
    elif status_type == 23:
        num = ccard.enhance_act_dur if ccard.is_downaction() else 0
    elif status_type == 24:
        num = ccard.enhance_avo_dur if ccard.is_downavoid() else 0
    elif status_type == 25:
        num = ccard.enhance_res_dur if ccard.is_downresist() else 0
    elif status_type == 26:
        num = ccard.enhance_def_dur if ccard.is_downdefense() else 0

    if num is None:
        return DecimalValue(0, line, pos)
    return DecimalValue(num, line, pos)


def _func_selectedcard(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StructureValue:
    """選択カードがある場合はカード情報を返す。存在しない場合は無効なカード情報を返す。"""
    _chk_argscount(args, 0, "SELECTEDCARD", line, pos)
    header = cw.cwpy.event.get_selectedcard()
    header_orig = header.ref_original() if header else None
    if header_orig is None:
        args2: List[Union[ValueType, Callable[[], ValueType]]] = [
            DecimalValue(decimal.Decimal(0), line, pos),
            DecimalValue(decimal.Decimal(0), line, pos),
            DecimalValue(decimal.Decimal(-2), line, pos),
        ]
        return StructureValue("cardinfo", args2, line, pos)
    assert header
    owner = header.get_owner()
    if cw.cwpy.ydata and cw.cwpy.ydata.storehouse is owner:
        castindex = -2
        cardindex = cw.cwpy.ydata.storehouse.index(header_orig) + 1
        actioncardid = -2
    elif cw.cwpy.ydata and cw.cwpy.ydata.party and cw.cwpy.ydata.party.backpack is owner:
        castindex = -1
        cardindex = cw.cwpy.ydata.party.backpack.index(header_orig) + 1
        actioncardid = -2
    else:
        assert isinstance(owner, cw.character.Character)
        castindex = _ccard_index(owner)
        if header_orig.type == "ActionCard":
            cardindex = 0
            actioncardid = header_orig.id
        else:
            pocket = cw.header.cardtype_to_pocket(header_orig.type)
            # CARDINDEXは特殊技能・アイテム・召喚獣全ての通し番号になる
            cardindex = owner.cardpocket[pocket].index(header_orig) + 1
            for i in range(0, pocket):
                cardindex += len(owner.cardpocket[i])
            actioncardid = -2
    args2 = [
        DecimalValue(decimal.Decimal(castindex), line, pos),
        DecimalValue(decimal.Decimal(cardindex), line, pos),
        DecimalValue(decimal.Decimal(actioncardid), line, pos),
    ]
    return StructureValue("cardinfo", args2, line, pos)


def _header_from(arg: ValueType, func_name: str, arg_index: int) -> Optional[cw.header.CardHeader]:
    info = _chk_structure(arg, func_name, arg_index, "cardinfo")
    castindex_v = info.eval(0)
    cardindex_v = info.eval(1)
    actioncardid_v = info.eval(2)
    assert isinstance(castindex_v, DecimalValue)
    assert isinstance(cardindex_v, DecimalValue)
    assert isinstance(actioncardid_v, DecimalValue)
    castindex = int(castindex_v.value)
    cardindex = int(cardindex_v.value)
    actioncardid = int(actioncardid_v.value)
    assert -2 <= castindex
    assert 0 <= cardindex
    if castindex == 0 or cardindex == 0:
        # アクションカード、もしくは無効なカード情報
        return cw.cwpy.rsrc.actioncards.get(actioncardid, None)
    if castindex == -2:
        # カード置場
        if cw.cwpy.ydata and cardindex <= len(cw.cwpy.ydata.storehouse):
            return cw.cwpy.ydata.storehouse[cardindex - 1]
        else:
            return None
    elif castindex == -1:
        # 荷物袋
        if cw.cwpy.ydata and cw.cwpy.ydata.party and cardindex <= len(cw.cwpy.ydata.party.backpack):
            return cw.cwpy.ydata.party.backpack[cardindex - 1]
        else:
            return None
    else:
        # キャラクター(CARDINDEXは特殊技能・アイテム・召喚獣全ての通し番号になる)
        ccard = _ccard_from(castindex_v, func_name)
        if ccard is None:
            return None
        for pocket in (cw.POCKET_SKILL, cw.POCKET_ITEM, cw.POCKET_BEAST):
            if cardindex <= len(ccard.cardpocket[pocket]):
                return ccard.cardpocket[pocket][cardindex - 1]
            cardindex -= len(ccard.cardpocket[pocket])
        return None


def _func_cardname(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """カード名を返す。カード情報が無効の場合は空文字列を返す。"""
    _chk_argscount(args, 1, "CARDNAME", line, pos)
    args_r = _all_eval(args)
    header = _header_from(args_r[0], "CARDNAME", 0)
    if header is None:
        return StringValue("", line, pos)
    else:
        return StringValue(header.get_showingname(), line, pos)


def _func_cardtype(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """
    カードのタイプを返す(特殊技能=1, アイテム=2, 召喚獣=3, アクションカード=-1)。
    カード情報が無効の場合は0を返す。
    """
    _chk_argscount(args, 1, "CARDTYPE", line, pos)
    args_r = _all_eval(args)
    header = _header_from(args_r[0], "CARDTYPE", 0)
    if header is None:
        return DecimalValue(0, line, pos)
    elif header.type == "ActionCard":
        return DecimalValue(-1, line, pos)
    else:
        return DecimalValue(cw.header.cardtype_to_pocket(header.type) + 1, line, pos)


def _func_cardrarity(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """
    カードの希少度を返す(一般=1, レア=2, プレミア=3)。
    カード情報が無効の場合は0を返す。
    """
    _chk_argscount(args, 1, "CARDRARITY", line, pos)
    args_r = _all_eval(args)
    header = _header_from(args_r[0], "CARDRARITY", 0)
    if header is None:
        return DecimalValue(-1, line, pos)
    elif header.premium == "Rare":
        return DecimalValue(1, line, pos)
    elif header.premium == "Premium":
        return DecimalValue(2, line, pos)
    else:
        return DecimalValue(0, line, pos)


def _func_cardprice(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """
    カードの価格を返す。
    カード情報が無効の場合は-1を返す。
    """
    _chk_argscount(args, 1, "CARDPRICE", line, pos)
    args_r = _all_eval(args)
    header = _header_from(args_r[0], "CARDPRICE", 0)
    if header is None:
        return DecimalValue(-1, line, pos)
    else:
        return DecimalValue(header.price, line, pos)


def _func_cardlevel(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """
    カードのレベルを返す。
    カード情報が無効か、特殊技能カードでない場合は-1を返す。
    """
    _chk_argscount(args, 1, "CARDLEVEL", line, pos)
    args_r = _all_eval(args)
    header = _header_from(args_r[0], "CARDLEVEL", 0)
    if header is None or header.type != "SkillCard":
        return DecimalValue(-1, line, pos)
    else:
        return DecimalValue(header.level, line, pos)


def _func_cardcount(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """
    カードの残り使用回数を返す。
    カード情報が無効の場合は-1を返す。
    """
    _chk_argscount(args, 1, "CARDCOUNT", line, pos)
    args_r = _all_eval(args)
    header = _header_from(args_r[0], "CARDCOUNT", 0)
    if header is None:
        return DecimalValue(-1, line, pos)
    elif header.type == "ActionCard":
        return DecimalValue(0, line, pos)
    else:
        return DecimalValue(header.uselimit, line, pos)


def _func_findkeycode(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> DecimalValue:
    """
    カードのキーコードをpatternで検索して見つかった位置（1～）を返す。
    キーコードが空文字列の場合は無視される。
    キーコードが見つからない・カード情報が無効の場合は 0 を返す。
    """
    _chk_argscount2(args, 2, 3, "FINDKEYCODE", line, pos)
    args_r = _all_eval(args)
    header = _header_from(args_r[0], "FINDKEYCODE", 0)
    pattern = _chk_string(args_r[1], "FINDKEYCODE", 0)
    if len(args_r) < 3:
        startpos = 1
    else:
        startpos = int(_chk_minvalue(args_r[2], "FINDKEYCODE", 0))
    startindex = startpos - 1
    if header is None:
        return DecimalValue(0, line, pos)

    reg = re.compile(fnmatch.translate(pattern))
    index = header.find_keycode_position_excluding_empty(lambda name: bool(reg.match(name)), startindex)
    return DecimalValue(index + 1, line, pos)


def _func_keycodetext(args: List[Callable[[], ValueType]], option: CalcOption, line: int, pos: int) -> StringValue:
    """
    カードのキーコード名を位置番号指定で返す。空文字列のキーコードがある位置は無視される。
    位置指定が無効の場合は空文字を返す。
    """
    _chk_argscount(args, 2, "KEYCODETEXT", line, pos)
    args_r = _all_eval(args)
    header = _header_from(args_r[0], "KEYCODETEXT", 0)
    index = int(_chk_minvalue(args_r[1], "KEYCODETEXT", 0)) - 1
    if header is None:
        return StringValue("", line, pos)

    keycode = ""
    try:
        keycode = header.get_keycode_at_excluding_empty(index)
    except IndexError:
        pass
    return StringValue(keycode, line, pos)


def _create_structure(info: StructureInfo, args: List[Callable[[], ValueType]], option: CalcOption, line: int,
                      pos: int) -> StructureValue:
    """構造体のインスタンスを生成する。"""
    uname = info.name.upper()
    if not info.is_public and option.evaltype not in ("Debugger", "Test"):
        raise ExprPermissionError("Structure %s is not accesible." % uname, info, None, line, pos)
    _chk_argscount2(args, info.required_member_num, len(info.members), uname, line, pos)

    args2: List[Union[ValueType, Callable[[], ValueType]]] = []
    args2.extend(args)
    for m in info.members[len(args):]:
        args2.append(_variantvalue_to_valuetype(m.defvalue, line, pos))

    return StructureValue(info.name, args2, line, pos)


_symbols = {
    # Wsn.5
    "player": decimal.Decimal(1),
    "enemy": decimal.Decimal(2),
    "friend": decimal.Decimal(3),
    "skill": decimal.Decimal(1),
    "item": decimal.Decimal(2),
    "beast": decimal.Decimal(3),
    "rare": decimal.Decimal(1),
    "premier": decimal.Decimal(2),
}


_functions = {
    # Wsn.4
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
    # Wsn.5
    "list": _func_list,
    "at": _func_at,
    "llen": _func_llen,
    "lfind": _func_lfind,
    "lleft": _func_lleft,
    "lright": _func_lright,
    "lmid": _func_lmid,
    "partymoney": _func_partymoney,
    "partynumber": _func_partynumber,
    "yadoname": _func_yadoname,
    "skintype": _func_skintype,
    "battleround": _func_battleround,
    "castlevel": _func_castlevel,
    "couponvalue": _func_couponvalue,
    "liferatio": _func_liferatio,
    "statusvalue": _func_statusvalue,
    "statusround": _func_statusround,
    "selectedcard": _func_selectedcard,
    "cardname": _func_cardname,
    "cardtype": _func_cardtype,
    "cardrarity": _func_cardrarity,
    "cardprice": _func_cardprice,
    "cardlevel": _func_cardlevel,
    "cardcount": _func_cardcount,
    "findkeycode": _func_findkeycode,
    "keycodetext": _func_keycodetext,
}


def _assert_s(expr: str, n: str) -> bool:
    val = calculate(parse(expr), CalcOption("Test", False))
    return _assert_s_val(val, n)


def _assert_s_val(val: ValueType, n: str) -> bool:
    assert isinstance(val, StringValue)
    return val.value == n


def _assert_d(expr: str, n: Union[int, decimal.Decimal]) -> bool:
    val = calculate(parse(expr), CalcOption("Test", False))
    return _assert_d_val(val, n)


def _assert_d_val(val: ValueType, n: Union[int, decimal.Decimal]) -> bool:
    assert isinstance(val, DecimalValue)
    return val.value == n


def _assert_b(expr: str, n: bool) -> bool:
    val = calculate(parse(expr), CalcOption("Test", False))
    return _assert_b_val(val, n)


def _assert_b_val(val: ValueType, n: bool) -> bool:
    assert isinstance(val, BooleanValue)
    return val.value is n


assert _assert_d("--5", 5)
assert _assert_d("---5", -5)
assert _assert_d("-(--5)", -5)
assert _assert_d("-- min(100,23)+5", 28)
assert _assert_d("+-Min(100,23)+ - 5", -28)
assert _assert_d("max (45, 42, 100.5,  23 ) + 0.123", decimal.Decimal("100.623"))
assert _assert_b("mAX(45,42,100.5,23)+0.123 = 100.623", True)
assert _assert_b("max(45,42,100.5,23)+0.123 <> 100.623", False)
assert _assert_b("true or false", True)
assert _assert_b("tRUe and faLSE", False)
assert _assert_b("true and true or false and false", True)
assert _assert_b("((true and true) or false) and false", False)
assert _assert_b("not false and true or false and false", True)
assert _assert_b("not false or false", True)
assert _assert_b("not not (false or false)", False)
assert _assert_b("not not not true", False)
assert _assert_b("not 1 = 2", True)
assert _assert_b("not 1 + 2 = 3", False)
assert _assert_b("nOT False And tRUe oR FALSE aND faLse", True)
assert _assert_b("NOT 1 + 2 = 3", False)
assert _assert_b("nOt 1 + 2 = 3", False)
assert _assert_s("(not true) ~ \"&\" ~ (not true)", "FALSE&FALSE")
assert _assert_d("(5+8) % 3", 1)
assert _assert_d("5 + 8%3", 7)
assert _assert_d("-2+22*2", 42)
assert _assert_d("9/3", 3)
assert _assert_b("4<=5", True)
assert _assert_b("4<=4", True)
assert _assert_b("4<=3", False)
assert _assert_b("5>=4", True)
assert _assert_b("4>=4", True)
assert _assert_b("3>=4", False)
assert _assert_b("4<5", True)
assert _assert_b("4<4", False)
assert _assert_b("4<3", False)
assert _assert_b("5>4", True)
assert _assert_b("4>4", False)
assert _assert_b("3>4", False)
assert _assert_b("5=4", False)
assert _assert_b("4=4", True)
assert _assert_b("3=4", False)
assert _assert_b("5<>4", True)
assert _assert_b("4<>4", False)
assert _assert_b("3<>4", True)
assert _assert_d("LEN(\"TESTあいうえお\")", 9)
assert _assert_d("FIND(\"対象文字列\", \"対象文字列\")", 1)
assert _assert_d("FIND(\"文字\", \"対象文字列\")", 3)
assert _assert_d("FIND(\"文じ\", \"対象文字列\")", 0)
assert _assert_d("FIND(\"文字\", \"対象文字列\", 3)", 3)
assert _assert_d("FIND(\"文字\", \"対象文字列\", 4)", 0)
assert _assert_d("FIND(\"文字\", \"対象文字列\", 0)", 0)
assert _assert_d("FIND(\"列\", \"対象文字列\", 5)", 5)
assert _assert_d("FIND(\"列\", \"対象文字列\", 6)", 0)
assert _assert_d("FIND(\"\", \"対象文字列\")", 1)
assert _assert_d("FIND(\"\", \"対象文字列\", 5)", 5)
assert _assert_d("FIND(\"\", \"対象文字列\", 6)", 0)
assert _assert_d("FIND(\"字\", \"A象B文C字D列\")", 6)
assert _assert_d("FIND(\"字\", \"A象B文C字D列\", 6)", 6)
assert _assert_d("FIND(\"字\", \"A象B文C字D列\", 7)", 0)
assert _assert_d("FIND(\"\", \"\")", 0)
assert _assert_d("find(\"列\", \"対象文字列\", 5)", 5)
assert _assert_d("fIND(\"列\", \"対象文字列\", 5)", 5)
assert _assert_s("LEFT(\"あいうえお\", 0)", "")
assert _assert_s("LEFT(\"あいうえお\", 3)", "あいう")
assert _assert_s("LEFT(\"あいうえお\", 8)", "あいうえお")
assert _assert_s("LEFT(\"あいうえお\", 8)", "あいうえお")
assert _assert_s("Left(\"あいうえお\", 8)", "あいうえお")
assert _assert_s("RIGHT(\"あいうえお\", 0)", "")
assert _assert_s("RIGHT(\"あいうえお\", 3)", "うえお")
assert _assert_s("RIGHT(\"あいうえお\", 8)", "あいうえお")
assert _assert_s("right(\"あいうえお\", 8)", "あいうえお")
assert _assert_s("MID(\"あいうえお\", 2, 3)", "いうえ")
assert _assert_s("MID(\"あいうえお\", 5, 3)", "お")
assert _assert_s("MID(\"あいうえお\", 6, 3)", "")
assert _assert_s("MID(\"あいうえお\", 3)", "うえお")
assert _assert_s("MID(\"あいうえお\", 5)", "お")
assert _assert_s("MID(\"あいうえお\", 6)", "")
assert _assert_s("MID(\"あいうえお\", 7)", "")
assert _assert_s("mId(\"あいうえお\", 7)", "")
assert _assert_s("STR(\"あいうえお\")", "あいうえお")
assert _assert_s("STR(42)", "42")
assert _assert_s("STR(42.42 + 5)", "47.42")
assert _assert_s("sTR(42.42 + 5)", "47.42")
assert _assert_d("VALUE(42.42 + 5)", decimal.Decimal("47.42"))
assert _assert_d("VALUE(42)", 42)
assert _assert_d("VALUE(\"42\")", 42)
assert _assert_d("VALUE(\"42.123\")", decimal.Decimal("42.123"))
assert _assert_d("VAluE(\"42.123\")", decimal.Decimal("42.123"))
assert _assert_d("INT(\"42.123\")", 42)
assert _assert_d("INT(\"42.9\")", 42)
assert _assert_d("INT(\" -42.9  \")", -42)
assert _assert_d("int(\" -42.9  \")", -42)
assert _assert_d("IF(1=2,99,88)", 88)
assert _assert_d("IF(2=2,99,88)", 99)
assert _assert_d("If(2=2,99,88)", 99)
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

_test_list1 = calculate(parse("LIST(\"STR\", 42, TRUE)"))
assert isinstance(_test_list1, ListValue)
assert len(_test_list1.value) == 3
assert _assert_s_val(_test_list1.eval(0), "STR")
assert _assert_d_val(_test_list1.eval(1), 42)
assert _assert_b_val(_test_list1.eval(2), True)

_test_list2 = calculate(parse("LIST(LIST(1, 2, 3), LIST(3, 4, 5))"))
assert isinstance(_test_list2, ListValue)
assert len(_test_list2.value) == 2
_test_list2_0 = _test_list2.eval(0)
assert isinstance(_test_list2_0, ListValue)
assert len(_test_list2_0.value) == 3
assert _assert_d_val(_test_list2_0.eval(0), 1)
assert _assert_d_val(_test_list2_0.eval(1), 2)
assert _assert_d_val(_test_list2_0.eval(2), 3)
_test_list2_1 = _test_list2.eval(1)
assert isinstance(_test_list2_1, ListValue)
assert len(_test_list2_1.value) == 3
assert _assert_d_val(_test_list2_1.eval(0), 3)
assert _assert_d_val(_test_list2_1.eval(1), 4)
assert _assert_d_val(_test_list2_1.eval(2), 5)

assert _assert_b("LIST(1, 2, 3) = LIST(1, 2, 3)", True)
assert _assert_b("LIST(1, 2, 3) = LIST(1, \"2\", 3)", False)
assert _assert_b("LIST(1, 2, 3) = LIST(1, 2)", False)
assert _assert_b("LIST(1, 2) = LIST(1, 2, 3)", False)
assert _assert_b("LIST(1, 2, 3) <> LIST(1, 2, 3)", False)
assert _assert_b("LIST(1, 2, 3) <> LIST(1, \"2\", 3)", True)
assert _assert_b("LIST(1, 2, 3) <> LIST(1, 2)", True)
assert _assert_b("LIST(1, 2) <> LIST(1, 2, 3)", True)
assert _assert_b("LIST(1, 2, 3) < LIST(1, 2, 3)", False)
assert _assert_b("LIST(1, 2, 3) < LIST(1, 2)", False)
assert _assert_b("LIST(1, 2, 3) < LIST(1, 3)", True)
assert _assert_b("LIST(1, 2) < LIST(1, 2, 3)", True)
assert _assert_b("LIST(1, 2, 3) <= LIST(1, 2, 3)", True)
assert _assert_b("LIST(1, 2, 3) <= LIST(1, 2)", False)
assert _assert_b("LIST(1, 2, 3) <= LIST(1, 3)", True)
assert _assert_b("LIST(1, 2) <= LIST(1, 2, 3)", True)
assert _assert_b("LIST(1, 2, 3) > LIST(1, 2, 3)", False)
assert _assert_b("LIST(1, 2, 3) > LIST(1, 2)", True)
assert _assert_b("LIST(1, 2) > LIST(1, 2, 3)", False)
assert _assert_b("LIST(1, 3) > LIST(1, 2, 3)", True)
assert _assert_b("LIST(1, 2, 3) >= LIST(1, 2, 3)", True)
assert _assert_b("LIST(1, 2, 3) >= LIST(1, 2)", True)
assert _assert_b("LIST(1, 2) >= LIST(1, 2, 3)", False)
assert _assert_b("LIST(1, 3) >= LIST(1, 2, 3)", True)
assert _assert_b("LIST(1, 2, 3) ~ LIST(4, 5, 6) = LIST(1, 2, 3, 4, 5, 6)", True)
assert _assert_b("LIST(1, 2, 3) ~ LIST(4, 5, 6) ~ LIST(7) = LIST(1, 2, 3, 4, 5, 6, 7)", True)

assert _assert_b("AT(LIST(TRUE, 42, \"STR\"), 1)", True)
assert _assert_d("AT(LIST(TRUE, 42, \"STR\"), 2)", 42)
assert _assert_s("AT(LIST(TRUE, 42, \"STR\"), 3)", "STR")
assert _assert_d("LLEN(LIST(1, 2, 3))", 3)
assert _assert_b("LLEFT(LIST(1, 2, 3), 2) = LIST(1, 2)", True)
assert _assert_b("LRIGHT(LIST(1, 2, 3), 2) = LIST(2, 3)", True)
assert _assert_b("LMID(LIST(1, 2, 3, 4), 2, 2) = LIST(2, 3)", True)
assert _assert_d("LFIND(3, LIST(1, 2, 3, 4))", 3)
assert _assert_d("LFIND(5, LIST(1, 2, 3, 4))", 0)
assert _assert_d("LFIND(\"TEST\", LIST(1, 2, \"TEST\", 4))", 3)
assert _assert_d("LFIND(LIST(99), LIST(1, 2, LIST(99), 4))", 3)
assert _assert_d("LFIND(42, LIST(42, 42, 4, 42), 3)", 4)
assert _assert_d("LFIND(42, LIST(42, 42, 42, 4), 3)", 3)

assert _assert_d("CARDINFO(4, 2).CASTINDEX", 4)
assert _assert_d("CARDINFO(4, 2).CARDINDEX", 2)
assert _assert_d("-CARDINFO(4, 2).CASTINDEX", -4)
assert _assert_d("---CARDINFO(4, 2).CASTINDEX", -4)
assert _assert_b("CARDINFO(4, 2).CASTINDEX = 4", True)
assert _assert_b("CARDINFO(4, 2) = CARDINFO(4, 2)", True)
assert _assert_b("CARDINFO(4, 2) <> CARDINFO(4, 2)", False)
assert _assert_b("CARDINFO(4, 2) = CARDINFO(5, 2)", False)
assert _assert_b("CARDINFO(4, 2) <> CARDINFO(5, 2)", True)
assert _assert_b("CARDINFO(4, 2) = CARDINFO(4, 3)", False)
assert _assert_b("CARDINFO(4, 2) <> CARDINFO(4, 3)", True)
assert _assert_b("LIST(CARDINFO(4, 2), CARDINFO(4, 2)) = LIST(CARDINFO(4, 2), CARDINFO(4, 2))", True)
assert _assert_b("LIST(CARDINFO(4, 2), CARDINFO(4, 2)) <> LIST(CARDINFO(4, 2), CARDINFO(4, 2))", False)
assert _assert_b("LIST(CARDINFO(4, 2), CARDINFO(4, 2)) = LIST(CARDINFO(4, 2), CARDINFO(4, 3))", False)
assert _assert_b("LIST(CARDINFO(4, 2), CARDINFO(4, 2)) <> LIST(CARDINFO(4, 2), CARDINFO(4, 3))", True)

assert _assert_d("PLAYER", 1)
assert _assert_d("ENEMY", 2)
assert _assert_d("FRIEND", 3)
assert _assert_d("SKILL", 1)
assert _assert_d("ITEM", 2)
assert _assert_d("BEAST", 3)
assert _assert_d("RARE", 1)
assert _assert_d("PREMIER", 2)
assert _assert_d("-PREMIER", -2)
assert _assert_d("-+--PREMIER + PLAYER", -1)
assert _assert_b("PLAYER = SKILL", True)
assert _assert_b("ENEMY > SKILL", True)
assert _assert_d("ENEMY + SKILL + PREMIER", 5)
assert _assert_s("MID(\"_test_\", enemy, Friend)", "tes")
assert _assert_b("LIST(FRIEND - RARE, \"X\" ~ PREMIER ~ PLAYER) = LIST(2, \"X21\")", True)


def main() -> None:
    st = parse(" ".join(sys.argv[1:]))
    print(st)
    print(calculate(st))


if __name__ == "__main__":
    main()
