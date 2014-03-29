#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
from ctypes import *

import cw

BASS_DEVICE_DEFAULT = 2
BASS_DEFAULT = 0
BASS_SAMPLE_LOOP = 4
BASS_MUSIC_STOPBACK = 0x80000
BASS_ATTRIB_VOL = 2
BASS_FILEPOS_CURRENT = 0
BASS_FILEPOS_END = 2
MIDI_EVENT_CONTROL = 64
BASS_SYNC_POS = 0
BASS_SYNC_END = 2
BASS_SYNC_MUSICPOS = 10
BASS_POS_BYTE = 0
CC111 = 111
MIDI_EVENT_END = 0
MIDI_EVENT_END_TRACK = 0x10003

_bass = None
_bassmidi = None
_sfonts = []
_bgmstream = 0
_soundstream1 = 0
_soundstream2 = 0

if sys.platform == "win32":
    SYNCPROC = WINFUNCTYPE(None, c_int, c_int, c_int, c_void_p)
else:
    SYNCPROC = CFUNCTYPE(None, c_int, c_int, c_int, c_void_p)

def _cc111loop(handle, channel, data, pos):
    """CC#111の位置へシークし、再び演奏を始める。"""
    _bass.BASS_ChannelSetPosition(channel, c_longlong(pos), BASS_POS_BYTE)
CC111LOOP = SYNCPROC(_cc111loop)

def is_alivable():
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    """BASS Audioによる演奏が可能な状態であればTrueを返す。
    init_bass()の実行前は必ずFalseを返す。"""
    return not _bass is None

def is_alivablemidi():
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    return _bassmidi and _sfonts

def is_alivablewithpath(path):
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    if os.path.splitext(path)[1].lower() in (".mid", ".midi"):
        return is_alivablemidi()
    else:
        return is_alivable()

def init_bass(soundfonts):
    """
    BASS AudioのDLLをロードし、再生のための初期化を行う。
    初期化が成功したらTrueを、失敗した場合はFalseを返す。
    soundfonts: サウンドフォントのファイルパス。listで指定。
    """
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2

    if _bass:
        # 初期化済み
        return True

    try:
        if sys.platform == "win32":
            _bass = windll.LoadLibrary("bass.dll")
            _bassmidi = windll.LoadLibrary("bassmidi.dll")
        else:
            if sys.maxsize == 0x7fffffff:
                _bass = CDLL("./lib/libbass32.so", mode=RTLD_GLOBAL)
                _bassmidi = CDLL("./lib/libbassmidi32.so")
            elif sys.maxsize == 0x7fffffffffffffff:
                _bass = CDLL("./lib/libbass64.so", mode=RTLD_GLOBAL)
                _bassmidi = CDLL("./lib/libbassmidi64.so")
    except Exception:
        cw.util.print_ex()

    if not _bass:
        return

    _bass.BASS_Init(-1, 44100, BASS_DEVICE_DEFAULT, None, None)

    # サウンドフォントのロード
    _sfonts = ""
    encoding = sys.getfilesystemencoding()
    if _bassmidi:
        for soundfont in soundfonts:
            sfont = _bassmidi.BASS_MIDI_FontInit(soundfont.encode(encoding), 0)
            if not sfont:
                print "BASS_MIDI_FontInit() failure: %s" % (soundfont)
                return False
            _sfonts += struct.pack("@iii", sfont, -1, 0)

        if not _sfonts:
            dispose_bass()
            return False

    return True

def _play(file, volume, loop):
    """
    BASS Audioによってfileを演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    loop: Trueならループ再生する。
    """
    global _bass, _bassmidi, _sfonts
    encoding = sys.getfilesystemencoding()
    flag = (BASS_MUSIC_STOPBACK|BASS_SAMPLE_LOOP) if loop else BASS_DEFAULT

    BASS_CONFIG_MIDI_DEFFONT = 0x10403
    ext = cw.util.splitext(file)[1].lower()
    if ext == ".mid" or ext == ".midi":
        if not is_alivablemidi():
            return
        stream = _bassmidi.BASS_MIDI_StreamCreateFile(False, file.encode(encoding), c_longlong(0), c_longlong(0), flag, 44100)
        if stream:
            if _sfonts:
                _bassmidi.BASS_MIDI_StreamSetFonts(stream, _sfonts, len(_sfonts) / (4*3))
            else:
                raise ValueError("sound font not found: %s" % (file))
        else:
            raise ValueError("_play() failure: %s" % (file))

        # RPGツクールで使用されるループ位置情報(CC#111)を探し、
        # 存在する場合はその位置からループ再生を行う
        count = _bassmidi.BASS_MIDI_StreamGetEvents(stream, -1, MIDI_EVENT_CONTROL, None)
        if count:
            events = "\0" * (count*4*5)
            count = _bassmidi.BASS_MIDI_StreamGetEvents(stream, -1, MIDI_EVENT_CONTROL, events)
            for i in xrange(0, count, 4*5):
                bassMidiEvent = struct.unpack("@iiiii", events[i:i+4*5])
                event = bassMidiEvent[0] # 使用しない
                param = bassMidiEvent[1]
                chan = bassMidiEvent[2] # 使用しない
                tick = bassMidiEvent[3] # 使用しない
                pos = bassMidiEvent[4]
                if param == CC111: # CC#111があったのでここでループする
                    _bass.BASS_ChannelSetSync(stream, BASS_SYNC_END, c_longlong(0), CC111LOOP, pos)
                    break
    else:
        stream = _bass.BASS_StreamCreateFile(False, file.encode(encoding), c_longlong(0), c_longlong(0), flag)
        if not stream:
            raise ValueError("_play() failure: %s" % (file))

    _bass.BASS_ChannelSetAttribute(stream, BASS_ATTRIB_VOL, c_float(volume))
    _bass.BASS_ChannelPlay(stream, loop)

    return stream

def dispose_bass():
    """全ての演奏を停止し、BASS AudioのDLLを解放する。"""
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    if not is_alivable():
        return

    if _bassmidi:
        for i in xrange(0, len(_sfonts), 4*3):
            sfont = struct.unpack("@Iii", _sfonts[i:i+4*3])
            _bassmidi.BASS_MIDI_FontFree(sfont[0])

    _bass.BASS_Free()
    del _bass
    _bass = None
    del _bassmidi
    _bassmidi = None

def play_bgm(file, volume=1.0):
    """
    BASS AudioによってfileをBGMとして演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    """
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    if not is_alivable():
        return False
    stop_bgm()
    _bgmstream = _play(file, volume, True)
    return _bgmstream <> 0

def play_sound(file, volume=1.0, fromscenario=False):
    """
    BASS Audioによってfileを効果音として演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    """
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    if not is_alivable():
        return False
    stop_sound(fromscenario)
    if fromscenario:
        _soundstream1 = _play(file, volume, False)
        return _soundstream1 <> 0
    else:
        _soundstream2 = _play(file, volume, False)
        return _soundstream2 <> 0

def stop_bgm():
    """BGMの再生を停止する。"""
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    if not is_alivable():
        return
    if _bgmstream:
        _bass.BASS_ChannelStop(_bgmstream)
        _bass.BASS_StreamFree(_bgmstream)
        _bgmstream = 0

def stop_sound(fromscenario=False):
    """効果音の再生を停止する。"""
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    if not is_alivable():
        return
    if fromscenario:
        if _soundstream1:
            _bass.BASS_ChannelStop(_soundstream1)
            _bass.BASS_StreamFree(_soundstream1)
            _soundstream1 = 0
    else:
        if _soundstream2:
            _bass.BASS_ChannelStop(_soundstream2)
            _bass.BASS_StreamFree(_soundstream2)
            _soundstream2 = 0

def set_bgmvolume(volume):
    """BGMの音量を変更する。"""
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    if not is_alivable():
        return
    if _bgmstream:
        _bass.BASS_ChannelSetAttribute(_bgmstream, BASS_ATTRIB_VOL, c_float(volume))

def set_soundvolume(volume):
    """効果音の音量を変更する。"""
    global _bass, _bassmidi, _sfonts, _bgmstream, _soundstream1, _soundstream2
    if not is_alivable():
        return
    if _soundstream1:
        _bass.BASS_ChannelSetAttribute(_soundstream1, BASS_ATTRIB_VOL, c_float(volume))
    if _soundstream2:
        _bass.BASS_ChannelSetAttribute(_soundstream2, BASS_ATTRIB_VOL, c_float(volume))

def main():
    import time
    print "Test BASS Audio. Sound Font: %s, File: %s, %s" % (sys.argv[1], sys.argv[2], sys.argv[3])
    init_bass([sys.argv[1]])
    play_bgm(sys.argv[2])
    time.sleep(200)
    play_sound(sys.argv[3])
    time.sleep(1)
    stop_bgm()
    stop_sound()
    dispose_bass()

if __name__ == "__main__":
    main()
