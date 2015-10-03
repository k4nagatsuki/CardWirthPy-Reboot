#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
import ctypes
from ctypes import c_size_t, c_long, c_void_p, c_longlong, c_float

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
BASS_SYNC_MIXTIME = 0x40000000
BASS_POS_BYTE = 0
MIDI_EVENT_END = 0
MIDI_EVENT_END_TRACK = 0x10003
BASS_TAG_OGG = 2
BASS_TAG_RIFF_INFO = 0x100
BASS_TAG_RIFF_BEXT = 0x101
BASS_TAG_RIFF_CART = 0x102
BASS_TAG_RIFF_DISP = 0x103
BASS_SAMPLE_8BITS = 1
BASS_SAMPLE_FLOAT = 256

STREAM_BGM = 0
STREAM_SOUND1 = 1
STREAM_SOUND2 = 2

CC111 = 111

_bass = None
_bassmidi = None
_sfonts = []

_streams = [0, 0, 0]
_loopstarts = [0, 0, 0]
_loopcounts = [0, 1, 1]

_bgmstream = 0
_soundstream1 = 0
_soundstream2 = 0

if sys.platform == "win32":
    SYNCPROC = ctypes.WINFUNCTYPE(None, c_size_t, c_long, c_long, c_void_p)
else:
    SYNCPROC = ctypes.CFUNCTYPE(None, c_size_t, c_long, c_long, c_void_p)

def _cc111loop(handle, channel, data, streamindex):
    """CC#111の位置へシークし、再び演奏を始める。"""
    global _bass, _loopcounts, _loopstarts
    if streamindex is None:
        streamindex = 0
    loops = _loopcounts[streamindex]
    if loops <> 1:
        if 0 < loops:
            _loopcounts[streamindex] = loops - 1
        pos = _loopstarts[streamindex]
        _bass.BASS_ChannelSetPosition(c_long(channel), c_longlong(pos), c_long(BASS_POS_BYTE))
CC111LOOP = SYNCPROC(_cc111loop)

def is_alivable():
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
    """BASS Audioによる演奏が可能な状態であればTrueを返す。
    init_bass()の実行前は必ずFalseを返す。"""
    return not _bass is None

def is_alivablemidi():
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
    return _bassmidi and _sfonts

def is_alivablewithpath(path):
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
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
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts

    if _bass:
        # 初期化済み
        return True

    try:
        if sys.platform == "win32":
            _bass = ctypes.windll.LoadLibrary("bass.dll")
            _bassmidi = ctypes.windll.LoadLibrary("bassmidi.dll")
        else:
            if sys.maxsize == 0x7fffffff:
                _bass = ctypes.CDLL("./lib/libbass32.so", mode=ctypes.RTLD_GLOBAL)
                _bassmidi = ctypes.CDLL("./lib/libbassmidi32.so")
            elif sys.maxsize == 0x7fffffffffffffff:
                _bass = ctypes.CDLL("./lib/libbass64.so", mode=ctypes.RTLD_GLOBAL)
                _bassmidi = ctypes.CDLL("./lib/libbassmidi64.so")
    except Exception:
        cw.util.print_ex()

    if not _bass:
        return False

    if not _bass.BASS_Init(-1, 44100, BASS_DEFAULT, None, None):
        dispose_bass()
        return False

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

def _play(fpath, volume, loopcount, streamindex):
    """
    BASS Audioによってfileを演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    loopcount: ループ回数。0で無限ループ。
    streamindex: 再生チャンネル番号。
    """
    global _bass, _bassmidi, _sfonts
    encoding = sys.getfilesystemencoding()
    flag = BASS_DEFAULT

    _BASS_CONFIG_MIDI_DEFFONT = 0x10403
    ismidi = False
    if os.path.isfile(fpath) and 4 <= os.path.getsize(fpath):
        with open(fpath, "rb") as f:
            head = f.read(4)
            f.close()
        ismidi = (head == "MThd")
    if ismidi:
        if not is_alivablemidi():
            return
        stream = _bassmidi.BASS_MIDI_StreamCreateFile(False, fpath.encode(encoding), c_longlong(0), c_longlong(0), flag, 44100)
        if stream:
            if _sfonts:
                _bassmidi.BASS_MIDI_StreamSetFonts(stream, _sfonts, len(_sfonts) / (4*3))
            else:
                raise ValueError("sound font not found: %s" % (fpath))
        else:
            raise ValueError("_play() failure: %s" % (fpath))

    else:
        stream = _bass.BASS_StreamCreateFile(False, fpath.encode(encoding), c_longlong(0), c_longlong(0), flag)
        if not stream:
            raise ValueError("_play() failure: %s" % (fpath))

    if loopcount <> 1:
        loopinfo = _get_loopinfo(fpath, stream)
    else:
        loopinfo = None

    if not loopinfo and ismidi:
        # RPGツクールで使用されるループ位置情報(CC#111)を探し、
        # 存在する場合はその位置からループ再生を行う
        count = _bassmidi.BASS_MIDI_StreamGetEvents(stream, -1, MIDI_EVENT_CONTROL, None)
        if count:
            events = "\0" * (count*4*5)
            count = _bassmidi.BASS_MIDI_StreamGetEvents(stream, -1, MIDI_EVENT_CONTROL, events)
            for i in xrange(0, count, 4*5):
                bassMidiEvent = struct.unpack("@iiiii", events[i:i+4*5])
                _event = bassMidiEvent[0] # 使用しない
                param = bassMidiEvent[1]
                _chan = bassMidiEvent[2] # 使用しない
                _tick = bassMidiEvent[3] # 使用しない
                pos = bassMidiEvent[4]
                if (param & 0x00ff) == CC111: # CC#111があったのでここでループする
                    loopinfo = (pos, -1)
                    break

    _loopcounts[streamindex] = loopcount
    if loopinfo:
        loopstart, loopend = loopinfo
        _loopstarts[streamindex] = loopstart
        if 0 <= loopend:
            _bass.BASS_ChannelSetSync(stream, BASS_SYNC_POS|BASS_SYNC_MIXTIME, c_longlong(loopend), CC111LOOP, streamindex)
        else:
            _bass.BASS_ChannelSetSync(stream, BASS_SYNC_END|BASS_SYNC_MIXTIME, c_longlong(0), CC111LOOP, streamindex)
    else:
        _loopstarts[streamindex] = 0
        _bass.BASS_ChannelSetSync(stream, BASS_SYNC_END|BASS_SYNC_MIXTIME, c_longlong(0), CC111LOOP, streamindex)

    _bass.BASS_ChannelSetAttribute(stream, BASS_ATTRIB_VOL, c_float(volume))
    _bass.BASS_ChannelPlay(stream, False)

    return stream

class BASS_CHANNELINFO(ctypes.Structure):
    _fields_ = [("freq", ctypes.c_int),
                ("chans", ctypes.c_int),
                ("flags", ctypes.c_int),
                ("ctype", ctypes.c_int),
                ("origres", ctypes.c_int),
                ("plugin", ctypes.c_void_p),
                ("sample", ctypes.c_void_p),
                ("filename", ctypes.c_char_p)]

def _get_loopinfo(fpath, stream):
    """吉里吉里もしくはRPGツクール形式の
    ループ情報が存在すれば取得して返す。
    """
    global _bass

    info = BASS_CHANNELINFO()
    pinfo = ctypes.byref(info)
    if not _bass.BASS_ChannelGetInfo(stream, pinfo):
        return None

    sampperbytes = 44100.0 / info.freq
    samptobytes = info.chans
    if info.flags & BASS_SAMPLE_FLOAT:
        samptobytes *= 4
    elif info.flags & BASS_SAMPLE_8BITS:
        samptobytes *= 1
    else:
        samptobytes *= 2

    # *.sliファイル
    sli = fpath + ".sli"
    if os.path.isfile(sli):
        try:
            with open(sli, "r") as f:
                s = f.read()
                f.close()
            for line in s.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if not line.startswith("Link"):
                    continue
                line = line[len("Link"):]
                start = line.find("{")
                end = line.rfind("}")
                if start == -1 or end == -1 or end < start:
                    continue
                line = line[start+1:end]
                secs = line.split(";")
                loopstart = -1
                loopend = -1
                for sec in secs:
                    if sec.startswith("From="):
                        loopend = int(sec[len("From="):])
                    if sec.startswith("To="):
                        loopstart = int(sec[len("To="):])
                if 0 <= loopstart:
                    loopstart = loopstart / sampperbytes
                    loopstart *= samptobytes
                    if 0 <= loopend:
                        loopend = loopend / sampperbytes
                        loopend *= samptobytes
                    return (int(loopstart), int(loopend))

        except:
            cw.util.print_ex()

    # Ogg Vorbisコメント埋め込み
    s = _bass.BASS_ChannelGetTags(stream, BASS_TAG_OGG)
    if s:
        comment = ctypes.string_at(s)
        loopstart = -1
        looplength = -1
        while comment:
            if comment.startswith("LOOPSTART="):
                loopstart = int(comment[len("LOOPSTART="):])
            if comment.startswith("LOOPLENGTH="):
                looplength = int(comment[len("LOOPLENGTH="):])
            s += len(comment)+1
            comment = ctypes.string_at(s)
        if 0 <= loopstart:
            if 0 <= looplength:
                loopend = loopstart + looplength
                loopend = loopend / sampperbytes
                loopend *= samptobytes
            else:
                loopend = -1
            loopstart = loopstart / sampperbytes
            loopstart *= samptobytes
            return (int(loopstart), int(loopend))

    return None

def dispose_bass():
    """全ての演奏を停止し、BASS AudioのDLLを解放する。"""
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
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

def play_bgm(fpath, volume=1.0, loopcount=0):
    """
    BASS AudioによってfileをBGMとして演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    """
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return False
    stop_bgm()
    _streams[STREAM_BGM] = _play(fpath, volume, loopcount, STREAM_BGM)
    return _streams[STREAM_BGM] <> 0

def play_sound(fpath, volume=1.0, fromscenario=False, loopcount=1):
    """
    BASS Audioによってfileを効果音として演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    """
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return False
    stop_sound(fromscenario)
    if fromscenario:
        _streams[STREAM_SOUND1] = _play(fpath, volume, loopcount, STREAM_SOUND1)
        return _streams[STREAM_SOUND1] <> 0
    else:
        _streams[STREAM_SOUND2] = _play(fpath, volume, loopcount, STREAM_SOUND2)
        return _streams[STREAM_SOUND2] <> 0

def stop_bgm():
    """BGMの再生を停止する。"""
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return
    if _streams[STREAM_BGM]:
        _bass.BASS_ChannelStop(_streams[STREAM_BGM])
        _bass.BASS_StreamFree(_streams[STREAM_BGM])
        _streams[STREAM_BGM] = 0

def stop_sound(fromscenario=False):
    """効果音の再生を停止する。"""
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return
    if fromscenario:
        if _streams[STREAM_SOUND1]:
            _bass.BASS_ChannelStop(_streams[STREAM_SOUND1])
            _bass.BASS_StreamFree(_streams[STREAM_SOUND1])
            _streams[STREAM_SOUND1] = 0
    else:
        if _streams[STREAM_SOUND2]:
            _bass.BASS_ChannelStop(_streams[STREAM_SOUND2])
            _bass.BASS_StreamFree(_streams[STREAM_SOUND2])
            _streams[STREAM_SOUND2] = 0

def set_bgmvolume(volume):
    """BGMの音量を変更する。"""
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return
    if _streams[STREAM_BGM]:
        _bass.BASS_ChannelSetAttribute(_streams[STREAM_BGM], BASS_ATTRIB_VOL, c_float(volume))

def set_soundvolume(volume):
    """効果音の音量を変更する。"""
    global _bass, _bassmidi, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return
    if _streams[STREAM_SOUND1]:
        _bass.BASS_ChannelSetAttribute(_streams[STREAM_SOUND1], BASS_ATTRIB_VOL, c_float(volume))
    if _streams[STREAM_SOUND2]:
        _bass.BASS_ChannelSetAttribute(_streams[STREAM_SOUND2], BASS_ATTRIB_VOL, c_float(volume))

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
