#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import struct


if sys.platform == "win32":
    _winapi = True
    import ctypes
    import win32api
    import win32con
else:
    _winapi = False

RT_CURSOR       = 1
RT_BITMAP       = 2
RT_ICON         = 3
RT_MENU         = 4
RT_DIALOG       = 5
RT_STRING       = 6
RT_FONTDIR      = 7
RT_FONT         = 8
RT_ACCELERATOR  = 9
RT_RCDATA       = 10
RT_MESSAGETABLE = 11
RT_GROUP_CURSOR = 12
RT_GROUP_ICON   = 14
RT_VERSION      = 16
RT_DLGINCLUDE   = 17
RT_PLUGPLAY     = 19
RT_VXD          = 20
RT_ANICURSOR    = 21
RT_ANIICON      = 22
RT_HTML         = 23
RT_MANIFEST     = 24

class Win32Res(object):
    """
    Win32以降のPEファイルからリソースを取得する。
    Win64用のPEファイルにも恐らく有効。
    """

    def __init__(self, file):
        object.__init__(self)

        self._table = {}
        self._winhandle = None

        if file:
            self.laod_resmodule(file)

    def __del__(self):
        self.dispose()

    def laod_resmodule(self, file):
        self._table = {}

        if _winapi:
            self._winhandle = win32api.LoadLibraryEx(file, 0,
                    win32con.LOAD_LIBRARY_AS_DATAFILE|
                    win32con.LOAD_WITH_ALTERED_SEARCH_PATH)
            if self._winhandle:
                return

        with open(file, "rb") as f:
            data = f.read()
        base = data[:]

        uint32 = struct.Struct("<L")
        uint16 = struct.Struct("<H")

        # MZ header
        if "MZ" <> data[:2]:
            raise Exception("")
        e_lfanew = uint32.unpack(data[60:64])[0]
        data = data[e_lfanew:]

        # PE header
        if "PE\0\0" <> data[:4]:
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
        for i in xrange(number_of_section):
            rva = uint32.unpack(data[12:16])[0]
            if ".rsrc" == data[:5] or res_addr_rva == rva:
                res_addr_rva == rva
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
        for i in xrange(num_name + num_id):
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
            for j in xrange(num_name + num_id):
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
                if 0 <> (w2 & 0x80000000):
                    raise Exception("")

                # IMAGE_RESOURCE_DATA_ENTRY
                res = base[w2+res_addr:]
                offset_to_data = uint32.unpack(res[:4])[0] - res_addr_rva + res_addr
                size = uint32.unpack(res[4:8])[0]

                res_data = base[offset_to_data:offset_to_data+size]

                if not name1 in self._table:
                    self._table[name1] = {}
                self._table[name1][name2] = res_data

    def _res_name(self, base, res_addr, uint16, w1):
        if 0x80000000 == (w1 & 0x80000000):
            # Name is String
            offset = (w1 & ~0x80000000) + res_addr
            len = uint16.unpack(base[offset:offset+2])[0]
            # wide chars
            return unicode(base[(offset+2):(offset+2)+(len*2)], "utf-16")
        else:
            # ID
            return w1

    def dispose(self):
        self._table = {}

        if self._winhandle:
            win32api.FreeLibrary(self._winhandle)
            self._winhandle = None

    def get_rcdata(self, type, name):
        if self._winhandle:
            k = ctypes.windll.kernel32
            if isinstance(type, (str, unicode)):
                type = ctypes.create_string_buffer(type)
            if isinstance(name, (str, unicode)):
                name = ctypes.create_string_buffer(name)
            hsrc = k.FindResourceA(self._winhandle, name, type)
            if hsrc:
                size = k.SizeofResource(self._winhandle, hsrc)
                hglobal = k.LoadResource(self._winhandle, hsrc)
                p = k.LockResource(hglobal)
                data = (ctypes.c_byte * size)()
                ctypes.memmove(data, p, size)
                return str(buffer(data))
        else:
            if type in self._table:
                table = self._table[type]
                if name in table:
                    return table[name]
        return None

    def get_bitmap(self, name):
        BITMAPFILEHEADER_SIZE = 14;
        RGBQUAD_SIZE = 4;

        data = self.get_rcdata(RT_BITMAP, name)
        if not data:
            return None

        uint32 = struct.Struct("<I")
        uint16 = struct.Struct("<H")

        # BITMAPINFOHEADER
        header_size = uint32.unpack(data[:4])[0]
        if header_size <> 40:
            raise Exception(header_size)
        bit_count = uint16.unpack(data[14:16])[0]
        clr_used = uint32.unpack(data[32:36])[0]

        # calclates data offset
        if clr_used == 0:
            if bit_count == 1:
                header_size += RGBQUAD_SIZE * (0x01 << 1)
            elif bit_count == 4:
                header_size += RGBQUAD_SIZE * (0x01 << 4)
            elif bit_count == 8:
                header_size += RGBQUAD_SIZE * (0x01 << 8)
            else:
                raise Exception("")
        else:
            header_size += RGBQUAD_SIZE * clr_used;
        header_size += BITMAPFILEHEADER_SIZE;
        size = BITMAPFILEHEADER_SIZE + len(data) # file size

        # BITMAPFILEHEADER
        header = "BM" + uint32.pack(size) + uint16.pack(0) + uint16.pack(0) + uint32.pack(header_size);
        assert len(header) == BITMAPFILEHEADER_SIZE

        return header + data;

    def get_tpf0form(self, name):
        data = self.get_rcdata(RT_RCDATA, name)
        if not data:
            return None
        if data[:4] <> "TPF0":
            return None
        data = data[4:]

        data = buffer(data)
        table = {}
        stack = [table]
        int8 = struct.Struct("b") # int8
        uint16 = struct.Struct("<H") # uint16(little endian)
        uint32 = struct.Struct("<I") # uint32(little endian)

        while 0 < len(data):
            length = ord(data[0])
            if length == 0:
                data = data[1:]
                stack.pop()
                continue
            classname = data[1:1+length]
            data = data[1+length:]
            length = ord(data[0])
            name = data[1:1+length]
            data = data[1+length:]
            c = {}
            stack[-1][name] = c
            stack.append(c)
            while True:
                length = ord(data[0])
                if length == 0:
                    data = data[1:]
                    break
                key = data[1:1+length]
                data = data[1+length:]
                type = ord(data[0])
                data = data[1:]
                if type == 0x01: # strings
                    value = []
                    while ord(data[0]) == 6:
                        length = ord(data[1])
                        value.append(unicode(data[2:2+length], "mbcs"))
                        data = data[2+length:]
                    data = data[1:]
                elif type == 0x02: # signed byte
                    value = int8.unpack(data[0])[0]
                    data = data[1:]
                elif type == 0x03: # unsigned short
                    value = uint16.unpack(data[:2])[0]
                    data = data[2:]
                elif type == 0x06: # string
                    length = ord(data[0])
                    value = unicode(data[1:1+length], "mbcs")
                    data = data[1+length:]
                elif type == 0x07: # name
                    length = ord(data[0])
                    value = data[1:1+length]
                    data = data[1+length:]
                elif type == 0x08: # False
                    value = False
                elif type == 0x09: # True
                    value = True
                elif type == 0x0a: # binary
                    length = uint32.unpack(data[0:4])[0]
                    value = data[4:4+length]
                    data = data[4+length:]
                elif type == 0x0b: # array
                    value = []
                    while 0 < ord(data[0]):
                        length = ord(data[0])
                        value.append(data[1:1+length])
                        data = data[1+length:]
                    data = data[1:]
                else:
                    raise Exception("value type: %s (%s, %s)" % (name, key, type))
                stack[-1][key] = value

        return table
