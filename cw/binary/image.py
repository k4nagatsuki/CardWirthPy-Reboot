#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64


BINARY_HEADER = "binaryimage://"

def path_is_code(path):
    """pathがバイナリイメージのテキスト表現であればTrue。"""
    return path.startswith(BINARY_HEADER)

def code_to_data(code):
    """テキスト表現codeをバイナリイメージへ変換する。"""
    if path_is_code(code):
        return base64.b64decode(code[len(BINARY_HEADER):])
    return ""

def data_to_code(data):
    """バイナリイメージdataをテキスト表現へ変換する。"""
    if len(data):
        return BINARY_HEADER + base64.b64encode(data)
    return ""
