#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ライブラリまたは実行ファイルからWindowsのリソースを取得する。"""

import os
import win32api, win32con
import ctypes
import struct
from ctypes import *


def get_bitmap(exe, resname):
    """exeからビットマップリソースを取得する。"""
    data = get_resource(exe, resname, win32con.RT_BITMAP)
    if not data:
        return None
    int16 = struct.Struct("<h") # int16(little endian)
    int32 = struct.Struct("<i") # int32(little endian)

    # ヘッダを生成する
    headersize = int16.unpack(data[:2])[0]
    arr = bytearray()
    arr += chr(0x42)
    arr += chr(0x4d)
    arr += int32.pack(len(data) + 14)
    arr += int16.pack(0)
    arr += int16.pack(0)
    arr += int32.pack(14 + headersize)

    # ビットマップ本体
    arr += data
    return str(arr)

def get_rcdata(exe, resname):
    """exeからオブジェクトテーブルを取得する。"""
    data = get_resource(exe, resname, win32con.RT_RCDATA)
    if not data:
        return None
    data = buffer(data)
    table = {}
    stack = []
    int8 = struct.Struct("b") # int8
    uint16 = struct.Struct("<H") # uint16(little endian)

    if data[0:4] == "TPF0":
        data = data[4:]
        while 0 < len(data):
            length = ord(data[0])
            if length == 0:
                data = data[1:]
                if len(stack):
                    stack.pop()
                    continue
                else:
                    break
            classname = data[1:1+length]
            data = data[1+length:]
            length = ord(data[0])
            name = data[1:1+length]
            data = data[1+length:]
            c = RCData(name, classname)
            if len(stack):
                stack[-1].table[name] = c
            else:
                table[name] = c
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
                if type == 0x02: # signed byte
                    value = int8.unpack(data[0])[0]
                    data = data[1:]
                elif type == 0x03: # unsigned short
                    value = uint16.unpack(data[:2])[0]
                    data = data[2:]
                elif type == 0x06: # string
                    length = ord(data[0])
                    value = unicode(data[1:1+length], 'ms932')
                    data = data[1+length:]
                elif type == 0x07: # name
                    length = ord(data[0])
                    value = data[1:1+length]
                    data = data[1+length:]
                elif type == 0x08: # False
                    value = False
                elif type == 0x09: # True
                    value = True
                elif type == 0x0b: # array
                    value = []
                    while 0 < ord(data[0]):
                        length = ord(data[0])
                        value.append(data[1:1+length])
                        data = data[1+length:]
                    data = data[1:]
                else:
                    raise Exception("value type: %s (%s, %s)" % (name, key, type))
                stack[-1].table[key] = value
    return data

class RCData:
    def __init__(self, name, classname):
        self.name = name
        self.classname = classname
        self.table = {}

def get_resource(exe, resname, type):
    """exeから特定型のリソースを取得する。"""
    handle = None
    try:
        k = ctypes.windll.kernel32
        handle = win32api.LoadLibraryEx(exe, 0, win32con.LOAD_LIBRARY_AS_DATAFILE | win32con.LOAD_WITH_ALTERED_SEARCH_PATH)
        if not handle:
            return ""
        hsrc = k.FindResourceA(handle, create_string_buffer(resname), type)
        data = None
        if hsrc:
            size = k.SizeofResource(handle, hsrc)
            hglobal = k.LoadResource(handle, hsrc)
            p = k.LockResource(hglobal)
            data = (ctypes.c_byte * size)()
            ctypes.memmove(data, p, size)
            data = str(buffer(data))
    finally:
        if handle: win32api.FreeLibrary(handle)
    return data
