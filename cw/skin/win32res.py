#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import struct

import cw

import typing
from typing import Dict, List, Optional, Sequence, TypeVar, Union

if sys.platform == "win32" and sys.maxsize == 0x7fffffff:
    _winapi = True
    import ctypes
else:
    _winapi = False

RT_CURSOR = 1
RT_BITMAP = 2
RT_ICON = 3
RT_MENU = 4
RT_DIALOG = 5
RT_STRING = 6
RT_FONTDIR = 7
RT_FONT = 8
RT_ACCELERATOR = 9
RT_RCDATA = 10
RT_MESSAGETABLE = 11
RT_GROUP_CURSOR = 12
RT_GROUP_ICON = 14
RT_VERSION = 16
RT_DLGINCLUDE = 17
RT_PLUGPLAY = 19
RT_VXD = 20
RT_ANICURSOR = 21
RT_ANIICON = 22
RT_HTML = 23
RT_MANIFEST = 24


class Win32Res(object):
    """
    Win32以降のPEファイルからリソースを取得する。
    Win64用のPEファイルにも恐らく有効。
    """

    def __init__(self, fpath: str) -> None:
        object.__init__(self)

        self._table: Dict[Union[str, int], Dict[Union[str, int], bytes]] = {}
        self._winhandle = None

        if fpath:
            self.laod_resmodule(fpath)

    def __del__(self) -> None:
        self.dispose()

    def laod_resmodule(self, fpath: str) -> None:
        self._table = {}

        if _winapi:
            fpath2 = ctypes.create_unicode_buffer(fpath)
            LOAD_LIBRARY_AS_DATAFILE = 0x00000002
            LOAD_WITH_ALTERED_SEARCH_PATH = 0x00000008
            self._winhandle = ctypes.windll.kernel32.LoadLibraryExW(
                fpath2, 0, LOAD_LIBRARY_AS_DATAFILE | LOAD_WITH_ALTERED_SEARCH_PATH
            )
            if self._winhandle:
                return

        with open(fpath, "rb") as f:
            data = f.read()
            f.close()
        base = data[:]

        uint32 = struct.Struct("<L")
        uint16 = struct.Struct("<H")

        # MZ header
        if b"MZ" != data[:2]:
            raise Exception("")
        e_lfanew = uint32.unpack(data[60:64])[0]
        data = data[e_lfanew:]

        # PE header
        if b"PE\0\0" != data[:4]:
            raise Exception("")
        data = data[4:]
        number_of_section = uint16.unpack(data[2:4])[0]
        size_of_option_header = uint16.unpack(data[16:18])[0]
        data = data[20:]

        # Resource section
        res_addr_rva = uint32.unpack(data[112:116])[0]
        data = data[size_of_option_header:]
        res_size = 0
        res_addr = 0
        for _i in range(number_of_section):
            rva = uint32.unpack(data[12:16])[0]
            if b".rsrc" == data[:5] or res_addr_rva == rva:
                res_addr_rva = rva
                res_size = uint32.unpack(data[16:20])[0]
                res_addr = uint32.unpack(data[20:24])[0]
                break
            data = data[40:]
        if res_size == 0:
            raise Exception("")
        data = base[res_addr:]

        # IMAGE_RESOURCE_DIRECTORY (Frame 1)
        num_name = uint16.unpack(data[12:14])[0]
        num_id = uint16.unpack(data[14:16])[0]
        data = data[16:]
        for _i in range(num_name + num_id):
            # IMAGE_RESOURCE_DIRECTORY_ENTRY (Frame 1)
            w1 = uint32.unpack(data[:4])[0]
            w2 = uint32.unpack(data[4:8])[0]
            data = data[8:]
            name1 = self._res_name(base, res_addr, uint16, w1)
            if (w2 & 0x80000000) == 0:
                raise Exception("")

            # IMAGE_RESOURCE_DIRECTORY (Frame 2)
            data2 = base[(w2 & ~0x80000000) + res_addr:]
            num_name = uint16.unpack(data2[12:14])[0]
            num_id = uint16.unpack(data2[14:16])[0]
            data2 = data2[16:]
            for _j in range(num_name + num_id):
                # IMAGE_RESOURCE_DIRECTORY_ENTRY (Frame 2)
                w1 = uint32.unpack(data2[:4])[0]
                w2 = uint32.unpack(data2[4:8])[0]
                data2 = data2[8:]
                name2 = self._res_name(base, res_addr, uint16, w1)

                if (w2 & 0x80000000) == 0:
                    raise Exception("")

                # IMAGE_RESOURCE_DIRECTORY (Frame 3)
                data3 = base[(w2 & ~0x80000000) + res_addr:]
                num_name = uint16.unpack(data3[12:14])[0]
                num_id = uint16.unpack(data3[14:16])[0]
                data3 = data3[16:]
                if num_name + num_id < 1:
                    raise Exception("")

                # IMAGE_RESOURCE_DIRECTORY_ENTRY (Frame 3)
                # ignore w1
                w2 = uint32.unpack(data3[4:8])[0]
                if 0 != (w2 & 0x80000000):
                    raise Exception("")

                # IMAGE_RESOURCE_DATA_ENTRY
                res = base[w2+res_addr:]
                offset_to_data = uint32.unpack(res[:4])[0] - res_addr_rva + res_addr
                size = uint32.unpack(res[4:8])[0]

                res_data = base[offset_to_data:offset_to_data+size]

                if name1 not in self._table:
                    self._table[name1] = {}
                self._table[name1][name2] = res_data

    def _res_name(self, base: bytes, res_addr: int, uint16: struct.Struct, w1: int) -> Union[str, int]:
        if 0x80000000 == (w1 & 0x80000000):
            # Name is String
            offset = (w1 & ~0x80000000) + res_addr
            length = uint16.unpack(base[offset:offset+2])[0]
            # wide chars
            return str(base[(offset+2):(offset+2)+(length*2)], "utf-16")
        else:
            # ID
            return w1

    def dispose(self) -> None:
        self._table = {}

        if self._winhandle:
            ctypes.windll.kernel32.FreeLibrary(self._winhandle)
            self._winhandle = None

    def get_rcdata(self, valtype: int, name: Union[int, bytes]) -> Optional[bytes]:
        if self._winhandle:
            k = ctypes.windll.kernel32
            if isinstance(valtype, bytes):
                valtype = ctypes.create_string_buffer(valtype)
            else:
                valtype = ctypes.c_char_p(valtype)
            name_key: Union[bytes, ctypes.c_char_p]
            if isinstance(name, bytes):
                name_key = ctypes.create_string_buffer(name)
            else:
                name_key = ctypes.c_char_p(name)
            hsrc = k.FindResourceA(self._winhandle, name_key, valtype)
            if hsrc:
                size = k.SizeofResource(self._winhandle, hsrc)
                hglobal = k.LoadResource(self._winhandle, hsrc)
                p = k.LockResource(hglobal)
                data = (ctypes.c_byte * size)()
                ctypes.memmove(data, p, size)
                return bytes(data)
        else:
            if valtype in self._table:
                table = self._table[valtype]
                if isinstance(name, bytes):
                    name_si: Union[str, int] = str(name, "utf-8")
                else:
                    name_si = name
                if name_si in table:
                    return table[name_si]
        return None

    def get_cursor(self, number: Union[int, str]) -> Optional[bytes]:
        ICONDIR_SIZE = 6
        ICONDIRENTRY_SIZE = 16

        uint32 = struct.Struct("<I")
        int32 = struct.Struct("<i")
        uint16 = struct.Struct("<H")
        uint8 = struct.Struct("<B")

        if isinstance(number, str):
            data = self.get_rcdata(RT_GROUP_CURSOR, number.encode("utf-8"))
            if not data:
                return None
            number_b: Union[int, bytes] = uint16.unpack(data[18:20])[0]
        else:
            number_b = number

        data = self.get_rcdata(RT_CURSOR, number_b)

        if not data:
            return None

        cursorcomponent = struct.Struct("<HH")
        xhotspot, yhotspot = cursorcomponent.unpack(data[:4])
        data = data[4:]

        header_size = uint32.unpack(data[:4])[0]
        if header_size != 40:
            raise Exception(header_size)

        width = uint32.unpack(data[4:8])[0]
        height = abs(int32.unpack(data[8:12])[0])
        bcbitcount = uint16.unpack(data[14:16])[0]
        copmression = uint32.unpack(data[16:20])[0]
        clrimportant = uint32.unpack(data[36:40])[0]

        if bcbitcount == 1 and copmression == 0 and clrimportant == 0:
            # bcbitcount == 1の場合はXORマスクとANDマスクが
            # 縦に並んでいるため、高さが2倍になっている
            height //= 2
            bcbitcount = 0

        size = len(data)

        iconfileheader = uint16.pack(0) + uint16.pack(2) + uint16.pack(1)

        icondirentry =\
            uint8.pack(width) +\
            uint8.pack(height) +\
            uint8.pack(bcbitcount) +\
            uint8.pack(0) +\
            uint16.pack(xhotspot) +\
            uint16.pack(yhotspot) +\
            uint32.pack(size) +\
            uint32.pack(ICONDIR_SIZE + ICONDIRENTRY_SIZE)

        return iconfileheader + icondirentry + data

    def get_bitmap(self, name: str) -> Optional[bytes]:
        BITMAPFILEHEADER_SIZE = 14
        RGBQUAD_SIZE = 4

        data = self.get_rcdata(RT_BITMAP, name.encode("utf-8"))
        if not data:
            return None

        uint32 = struct.Struct("<I")
        uint16 = struct.Struct("<H")

        # BITMAPINFOHEADER
        header_size = uint32.unpack(data[:4])[0]
        if header_size != 40:
            raise Exception(header_size)
        bit_count = uint16.unpack(data[14:16])[0]
        clr_used = uint32.unpack(data[32:36])[0]

        # calculates data offset
        if clr_used == 0:
            if bit_count == 1:
                header_size += RGBQUAD_SIZE * (0x01 << 1)
            elif bit_count == 4:
                header_size += RGBQUAD_SIZE * (0x01 << 4)
            elif bit_count == 8:
                header_size += RGBQUAD_SIZE * (0x01 << 8)
            else:
                pass
        else:
            header_size += RGBQUAD_SIZE * clr_used
        header_size += BITMAPFILEHEADER_SIZE
        size = BITMAPFILEHEADER_SIZE + len(data)  # file size

        # BITMAPFILEHEADER
        header = b"BM" + uint32.pack(size) + uint16.pack(0) + uint16.pack(0) + uint32.pack(header_size)
        assert len(header) == BITMAPFILEHEADER_SIZE

        return header + data

    def get_tpf0form(self, name: bytes) -> Optional["ResTable"]:
        data = self.get_rcdata(RT_RCDATA, name)
        if not data:
            return None
        if data[:4] != b"TPF0":
            return None
        data = data[4:]

        table = ResTable()
        stack: List[ResTable] = [table]
        int8 = struct.Struct("b")  # int8
        uint8 = struct.Struct("B")  # uint8
        uint16 = struct.Struct("<H")  # uint16(little endian)
        uint32 = struct.Struct("<I")  # uint32(little endian)

        while 0 < len(data):
            length = data[0]
            if length == 0:
                data = data[1:]
                stack.pop()
                continue
            # classname = data[1:1+length]
            data = data[1+length:]
            length = data[0]
            name = data[1:1+length]
            data = data[1+length:]
            c = ResTable()
            stack[-1].table[name] = c
            stack.append(c)
            while True:
                length = data[0]
                if length == 0:
                    data = data[1:]
                    break
                key = data[1:1+length]
                data = data[1+length:]
                valtype = data[0]
                data = data[1:]
                value: Union[List[str], int, str, bool, bytes, List[bytes]]
                if valtype == 0x01:  # strings
                    seq = []
                    while data[0] in (2, 3, 6):
                        dt = data[0]
                        if dt == 2:
                            seq.append(uint8.unpack(data[1:2])[0])
                            data = data[2:]
                        elif dt == 3:
                            seq.append(uint16.unpack(data[1:3])[0])
                            data = data[3:]
                        elif dt == 6:
                            length = data[1]
                            seq.append(str(data[2:2+length], cw.MBCS))
                            data = data[2+length:]
                    data = data[1:]
                    value = seq
                elif valtype == 0x02:  # signed byte
                    value = int8.unpack(data[:1])[0]
                    data = data[1:]
                elif valtype == 0x03:  # unsigned short
                    value = uint16.unpack(data[:2])[0]
                    data = data[2:]
                elif valtype == 0x06:  # string
                    length = data[0]
                    value = str(data[1:1+length], cw.MBCS)
                    data = data[1+length:]
                elif valtype == 0x07:  # name
                    length = data[0]
                    value = str(data[1:1+length], cw.MBCS)
                    data = data[1+length:]
                elif valtype == 0x08:  # False
                    value = False
                elif valtype == 0x09:  # True
                    value = True
                elif valtype == 0x0a:  # binary
                    length = uint32.unpack(data[0:4])[0]
                    value = data[4:4+length]
                    data = data[4+length:]
                elif valtype == 0x0b:  # array
                    seq = []
                    while 0 < data[0]:
                        length = data[0]
                        seq.append(data[1:1+length])
                        data = data[1+length:]
                    data = data[1:]
                    value = seq
                elif valtype == 0x12:  # unknown (utf-16 string?)
                    length = uint32.unpack(data[:4])[0]
                    length *= 2
                    value = str(data[4:4+length], "utf-16")
                    data = data[4+length:]
                else:
                    raise Exception("value type: %s (%s, %s)" % (str(name, cw.MBCS), str(key, cw.MBCS), valtype))
                stack[-1].table[key] = value

        return table


class ResTable(object):
    def __init__(self) -> None:
        self.table: Dict[bytes, Union[List[str], int, str, bool, bytes, List[bytes], ResTable]] = {}


ResType = TypeVar("ResType", List[str], int, str, bool, bytes, List[bytes], ResTable)


@typing.overload
def find_res(table: ResTable, path_l: Sequence[bytes], defvalue: List[str]) -> List[str]: ...


@typing.overload
def find_res(table: ResTable, path_l: Sequence[bytes], defvalue: bool) -> bool: ...


@typing.overload
def find_res(table: ResTable, path_l: Sequence[bytes], defvalue: int) -> int: ...


@typing.overload
def find_res(table: ResTable, path_l: Sequence[bytes], defvalue: str) -> str: ...


@typing.overload
def find_res(table: ResTable, path_l: Sequence[bytes], defvalue: bytes) -> bytes: ...


@typing.overload
def find_res(table: ResTable, path_l: Sequence[bytes], defvalue: List[bytes]) -> List[bytes]: ...


@typing.overload
def find_res(table: ResTable, path_l: Sequence[bytes], defvalue: ResTable) -> ResTable: ...


def find_res(table: ResTable, path_l: Sequence[bytes],
             defvalue: Union[List[str], bool, int, str, bytes, List[bytes], ResTable])\
        -> Union[List[str], bool, int, str, bytes, List[bytes], ResTable]:
    assert 0 < len(path_l)
    if path_l[0] not in table.table:
        return defvalue
    table2 = table.table[path_l[0]]
    if len(path_l) == 1:
        if type(table2) is type(defvalue):
            return table2
        else:
            return defvalue
    elif isinstance(table2, ResTable):
        return find_res(table2, path_l[1:], defvalue)
    else:
        return defvalue


def main() -> None:
    pass


if __name__ == "__main__":
    main()
