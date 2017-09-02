#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import struct
import ctypes
import threading
from ctypes import c_size_t, c_long, c_void_p, c_longlong, c_float

import cw
from cw.util import synclock

BASS_DEVICE_DEFAULT = 0
BASS_DEVICE_8BITS = 1
BASS_DEVICE_MONO = 2
BASS_DEVICE_3D = 4

BASS_DEFAULT = 0
BASS_SAMPLE_LOOP = 4
BASS_MUSIC_RAMP = 0x200
BASS_MUSIC_RAMPS = 0x400
BASS_MUSIC_POSRESET = 0x8000
BASS_MUSIC_PRESCAN = 0x20000
BASS_MUSIC_STOPBACK = 0x80000
BASS_FILEPOS_CURRENT = 0
BASS_FILEPOS_END = 2
MIDI_EVENT_CONTROL = 64
BASS_SYNC_POS = 0
BASS_SYNC_END = 2
BASS_SYNC_SLIDE = 5
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
BASS_ACTIVE_STOPPED = 0
BASS_ATTRIB_TEMPO = 0x10000
BASS_ATTRIB_TEMPO_PITCH = 0x10001
BASS_ATTRIB_TEMPO_FREQ = 0x10002
BASS_ATTRIB_FREQ = 1
BASS_ATTRIB_VOL = 2
BASS_ATTRIB_PAN = 3
BASS_ATTRIB_EAXMIX = 4
BASS_ATTRIB_MUSIC_AMPLIFY = 0x100
BASS_ATTRIB_MUSIC_PANSEP = 0x101
BASS_ATTRIB_MUSIC_PSCALER = 0x102
BASS_ATTRIB_MUSIC_BPM = 0x103
BASS_ATTRIB_MUSIC_SPEED = 0x104
BASS_ATTRIB_MUSIC_VOL_GLOBAL = 0x105
BASS_ATTRIB_MUSIC_VOL_CHAN = 0x200 # + channel No.
BASS_ATTRIB_MUSIC_VOL_INST = 0x300 # + instrument No.
BASS_STREAM_DECODE = 0x200000
BASS_FX_FREESOURCE = 0x10000

MAX_BGM_CHANNELS = 2
MAX_SOUND_CHANNELS = 2

STREAM_BGM = 0 # 0～1
STREAM_SOUND1 = 2 # 2～3
STREAM_SOUND2 = 4 # 4

CC111 = 111

_bass = None
_bassmidi = None
_bassfx = None
_sfonts = []

_streams = [0, 0, 0, 0, 0]
_fadeoutstreams = [None, None, None, None, None]
_loopstarts = [0, 0, 0, 0, 0]
_loopcounts = [0, 1, 1, 1, 1]

_lock = threading.Lock()
_fadeoutlock = threading.Lock()

if sys.platform == "win32":
    SYNCPROC = ctypes.WINFUNCTYPE(None, c_size_t, c_long, c_long, c_void_p)
else:
    SYNCPROC = ctypes.CFUNCTYPE(None, c_size_t, c_long, c_long, c_void_p)

def _cc111loop(handle, channel, data, streamindex):
    """CC#111の位置へシークし、再び演奏を始める。"""
    if streamindex is None:
        streamindex = 0
    _loop(handle, channel, data, streamindex)
CC111LOOP = SYNCPROC(_cc111loop)

def _free_channel(handle, channel, data, streamindex):
    global _bass, _fadeoutstreams
    _bass.BASS_ChannelStop(channel)
    _bass.BASS_StreamFree(channel)
    if streamindex is None:
        streamindex = 0

    @synclock(_fadeoutlock)
    def func(streamindex):
        _fadeoutstreams[streamindex] = None
    func(streamindex)

def _free_channel_lockfree(handle, channel, data, streamindex):
    global _bass, _fadeoutstreams
    _bass.BASS_ChannelStop(channel)
    _bass.BASS_StreamFree(channel)
    if streamindex is None:
        streamindex = 0
    _fadeoutstreams[streamindex] = None

FREE_CHANNEL = SYNCPROC(_free_channel)

@synclock(_lock)
def _loop(handle, channel, data, streamindex):
    global _bass, _loopcounts, _loopstarts, _fadeoutstreams
    fadeouting = _fadeoutstreams[streamindex] and _fadeoutstreams[streamindex][0] == channel
    if fadeouting:
        # フェードアウト中のチャンネル
        loops = _fadeoutstreams[streamindex][1]
        pos = _fadeoutstreams[streamindex][2]
    else:
        loops = _loopcounts[streamindex]
        pos = _loopstarts[streamindex]

    if loops <> 1:
        if 0 < loops:
            if fadeouting:
                _fadeoutstreams[streamindex] = (channel, loops - 1, pos)
            else:
                _loopcounts[streamindex] = loops - 1
        _bass.BASS_ChannelSetPosition(c_long(channel), c_longlong(pos), c_long(BASS_POS_BYTE))

def is_alivable():
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    """BASS Audioによる演奏が可能な状態であればTrueを返す。
    init_bass()の実行前は必ずFalseを返す。"""
    return not _bass is None

def is_alivablemidi():
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    return _bassmidi and _sfonts

def is_alivablewithpath(path):
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
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
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts

    if _bass:
        # 初期化済み
        return True

    try:
        if sys.platform == "win32":
            _bass = ctypes.windll.LoadLibrary("bass.dll")
            _bassmidi = ctypes.windll.LoadLibrary("bassmidi.dll")
            _bassfx = ctypes.windll.LoadLibrary("bass_fx.dll")
        else:
            if sys.maxsize == 0x7fffffff:
                _bass = ctypes.CDLL("./lib/libbass32.so", mode=ctypes.RTLD_GLOBAL)
                _bassmidi = ctypes.CDLL("./lib/libbassmidi32.so")
                _bassfx = ctypes.CDLL("./lib/libbass_fx32.so")
            elif sys.maxsize == 0x7fffffffffffffff:
                _bass = ctypes.CDLL("./lib/libbass64.so", mode=ctypes.RTLD_GLOBAL)
                _bassmidi = ctypes.CDLL("./lib/libbassmidi64.so")
                _bassfx = ctypes.CDLL("./lib/libbass_fx64.so")
    except Exception:
        cw.util.print_ex()

    if not _bass:
        return False

    if not _bass.BASS_Init(-1, 44100, BASS_DEVICE_DEFAULT, None, None):
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

def change_soundfonts(soundfonts):
    """サウンドフォントの差し替えを行う。"""
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    if _bassmidi:
        for i in xrange(0, len(_sfonts), 4*3):
            sfont = struct.unpack("@Iii", _sfonts[i:i+4*3])
            _bassmidi.BASS_MIDI_FontFree(sfont[0])

        _sfonts = ""
        encoding = sys.getfilesystemencoding()
        for soundfont in soundfonts:
            sfont = _bassmidi.BASS_MIDI_FontInit(soundfont.encode(encoding), 0)
            if not sfont:
                print "BASS_MIDI_FontInit() failure: %s" % (soundfont)
                return False
            _sfonts += struct.pack("@iii", sfont, -1, 0)

        if not _sfonts:
            return False

    return True

def _play(fpath, volume, loopcount, streamindex, fade, tempo=0, pitch=0):
    """
    BASS Audioによってfileを演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    loopcount: ループ回数。0で無限ループ。
    streamindex: 再生チャンネル番号。
    fade: フェードインにかける時間(ミリ秒)。
    tempo: テンポを変更する場合は-95%～5000%の値を指定。
    pitch: ピッチを変更する場合は-60～60の値を指定。
    """
    global _bass, _bassmidi, _bassfx, _sfonts
    encoding = sys.getfilesystemencoding()
    flag = BASS_MUSIC_STOPBACK|BASS_MUSIC_POSRESET|BASS_MUSIC_PRESCAN
    if tempo <> 0 or pitch <> 0:
        flag |= BASS_STREAM_DECODE

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

    if tempo <> 0 or pitch <> 0:
        stream = _bassfx.BASS_FX_TempoCreate(stream, BASS_FX_FREESOURCE)

    _loopcounts[streamindex] = loopcount
    if loopinfo:
        loopstart, loopend = loopinfo
        _loopstarts[streamindex] = loopstart
        if 0 <= loopend:
            _bass.BASS_ChannelSetSync(stream, BASS_SYNC_POS|BASS_SYNC_MIXTIME, c_longlong(loopend), CC111LOOP, c_void_p(streamindex))
        else:
            _bass.BASS_ChannelSetSync(stream, BASS_SYNC_END|BASS_SYNC_MIXTIME, c_longlong(0), CC111LOOP, c_void_p(streamindex))
    else:
        _loopstarts[streamindex] = 0
        _bass.BASS_ChannelSetSync(stream, BASS_SYNC_END|BASS_SYNC_MIXTIME, c_longlong(0), CC111LOOP, c_void_p(streamindex))

    if tempo <> 0:
        _bass.BASS_ChannelSetAttribute(stream, BASS_ATTRIB_TEMPO, c_float(tempo)) # -95%...0...+5000%
    if pitch <> 0:
        _bass.BASS_ChannelSetAttribute(stream, BASS_ATTRIB_TEMPO_PITCH, c_float(pitch)) # -60...0...+60

    if 0 < fade:
        _bass.BASS_ChannelSetAttribute(stream, BASS_ATTRIB_VOL, c_float(0))
        _bass.BASS_ChannelSlideAttribute(stream, BASS_ATTRIB_VOL, c_float(volume), c_long(fade))
    else:
        _bass.BASS_ChannelSetAttribute(stream, BASS_ATTRIB_VOL, c_float(volume))
    _bass.BASS_ChannelPlay(stream, False)

    return stream

def _get_attribute(stream, flag):
    global _bass
    class ATTR(ctypes.Structure):
        _fields_ = [("value", ctypes.c_float)]
    attr = ATTR()
    _bass.BASS_ChannelGetAttribute(stream, flag, ctypes.byref(attr))
    return attr.value

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
                    sec = sec.strip()
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

@synclock(_lock)
def set_loopcount(loopcount, streamindex):
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    if not _streams[streamindex]:
        return
    if _bass.BASS_ChannelIsActive(_streams[streamindex]) == BASS_ACTIVE_STOPPED:
        # 終了していた場合は再開
        _loopcounts[streamindex] = loopcount
        _bass.BASS_ChannelPlay(_streams[streamindex], False)
    else:
        if 1 <= loopcount:
            # 現在のループが終わってから次の設定開始
            loopcount += 1
        _loopcounts[streamindex] = loopcount

def dispose_bass():
    """全ての演奏を停止し、BASS AudioのDLLを解放する。"""
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
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

def play_bgm(fpath, volume=1.0, loopcount=0, channel=0, fade=0):
    """
    BASS AudioによってfileをBGMとして演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    loopcount: ループ回数。
    channel: 再生チャンネル。現在は0～1。
    fade: フェードインにかける時間(ミリ秒)。
    """
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return False
    if 1 < channel:
        return False
    stop_bgm(channel, fade=fade)
    channel += STREAM_BGM
    _streams[channel] = _play(fpath, volume, loopcount, channel, fade)
    return _streams[channel] <> 0

def set_bgmloopcount(loopcount, channel=0):
    set_loopcount(loopcount, STREAM_BGM+channel)

def play_sound(fpath, volume=1.0, fromscenario=False, loopcount=1, channel=0, fade=0):
    """
    BASS Audioによってfileを効果音として演奏する。
    file: 再生するファイル。
    volume: 音量。0.0～1.0で指定。
    channel: 再生チャンネル。現在は0～1。
    fade: フェードインにかける時間(ミリ秒)。
    """
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return False
    if 1 < channel:
        return False
    stop_sound(fromscenario, channel, fade=fade)
    if fromscenario:
        channel += STREAM_SOUND1
        _streams[channel] = _play(fpath, volume, loopcount, channel, fade)
        return _streams[channel] <> 0
    else:
        _streams[STREAM_SOUND2] = _play(fpath, volume, loopcount, STREAM_SOUND2, fade)
        return _streams[STREAM_SOUND2] <> 0

def _stop(streamindex, fade, stopfadeout):
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _fadeoutstreams, _loopstarts, _loopcounts

    if stopfadeout:
        _free_fadeoutstream(streamindex)

    if _streams[streamindex]:
        stream = _streams[streamindex]
        if 0 < fade:
            _free_fadeoutstream(streamindex)

            _bass.BASS_ChannelSetSync(stream, BASS_SYNC_SLIDE, c_longlong(0), FREE_CHANNEL, c_void_p(streamindex))
            _bass.BASS_ChannelSlideAttribute(stream, BASS_ATTRIB_VOL, c_float(0), c_long(fade))
            @synclock(_fadeoutlock)
            def func(stream):
                _fadeoutstreams[streamindex] = (stream, _loopcounts[streamindex], _loopstarts[streamindex])
            func(stream)
        else:
            _free_channel(None, stream, 0, streamindex)
        _streams[streamindex] = 0

@synclock(_fadeoutlock)
def _free_fadeoutstream(streamindex):
    if _fadeoutstreams[streamindex]:
        channel = _fadeoutstreams[streamindex][0]
        _free_channel_lockfree(None, channel, 0, streamindex)

def stop_bgm(channel=0, fade=0, stopfadeout=False):
    """BGMの再生を停止する。
    channel: 再生を停止するチャンネル。
    fade: フェードアウトにかける秒数(ミリ秒)。
    """
    if not is_alivable():
        return
    channel += STREAM_BGM
    _stop(channel, fade, stopfadeout=stopfadeout)

def stop_sound(fromscenario=False, channel=0, fade=0, stopfadeout=False):
    """効果音の再生を停止する。"""
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return
    if fromscenario:
        channel += STREAM_SOUND1
        _stop(channel, fade=fade, stopfadeout=stopfadeout)
    else:
        _stop(STREAM_SOUND2, fade=fade, stopfadeout=stopfadeout)

def _set_volume(volume, streamindex, fade):
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _fadeoutstreams, _loopstarts, _loopcounts
    if _fadeoutstreams[streamindex] and volume == 0 and fade == 0:
        _bass.BASS_ChannelStop(_fadeoutstreams[streamindex][0])
        _bass.BASS_StreamFree(_fadeoutstreams[streamindex][0])
        _fadeoutstreams[streamindex] = None

    if _streams[streamindex]:
        _bass.BASS_ChannelSlideAttribute(_streams[streamindex], BASS_ATTRIB_VOL, c_float(volume), c_long(fade))

def set_bgmvolume(volume, channel=0, fade=0):
    """BGMの音量を変更する。"""
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return
    channel += STREAM_BGM
    _set_volume(volume, channel, fade)

def set_soundvolume(volume, fromscenario=False, channel=0, fade=0):
    """効果音の音量を変更する。"""
    global _bass, _bassmidi, _bassfx, _sfonts, _streams, _loopstarts, _loopcounts
    if not is_alivable():
        return
    if fromscenario:
        channel += STREAM_SOUND1
        _set_volume(volume, channel, fade)
    else:
        _set_volume(volume, STREAM_SOUND2, fade)

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
