#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

static int
intwrap(int i, int min, int max)
{
    if (i > max)
        i = max;
    else if (i < min)
        i = min;

    return i;
}

#define colorwrap(i) intwrap(i, 0, 255)

static int
equals_rgb(unsigned char *data1, size_t index1, int r, int g, int b)
{
    if (data1[index1 + 0] != r) return 0;
    if (data1[index1 + 1] != g) return 0;
    if (data1[index1 + 2] != b) return 0;
    return 1;
}

static PyObject *
add_mosaic(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t len;
    int w, h, x, y, x2, y2, val;
    unsigned char *data, *outdata;
    unsigned long idx;

    if (!PyArg_ParseTuple(args, "s#(ii)i", &data, &len, &w, &h, &val))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &len);
    val = intwrap(val, 0, 255);
    if (!val)
    {
        return string;
    }

    for (y = 0; y < h; y++)
    {
        y2 = (y / val) * val;

        for (x = 0; x < w; x++)
        {
            x2 = (x / val) * val;
            idx = (y2 * w + x2) * 4;
            outdata[0] = data[idx];
            outdata[1] = data[idx + 1];
            outdata[2] = data[idx + 2];
            outdata[3] = data[idx + 3];
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
to_binaryformat(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t len;
    int w, h, x, y, val, br, bg, bb;
    unsigned char *data, *outdata;
    unsigned char r, g, b;

    if (!PyArg_ParseTuple(args, "s#(ii)i(iii)", &data, &len, &w, &h, &val, &br, &bg, &bb))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &len);
    val = intwrap(val, -1, 255);

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            r = data[0];
            g = data[1];
            b = data[2];

            if (val == -1 ? (r != br || g != bg || b != bb) : (r <= val && g <= val && b <= val))
            {
                outdata[0] = 0;
                outdata[1] = 0;
                outdata[2] = 0;
                outdata[3] = data[3];
            }
            else
            {
                outdata[0] = 255;
                outdata[1] = 255;
                outdata[2] = 255;
                outdata[3] = data[3];
            }
            data += 4;
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
add_noise(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t len;
    int r, g, b, w, h, x, y, val, randmax, i, colornoise = 0;
    unsigned char *data, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)i|i", &data, &len, &w, &h, &val,
                &colornoise))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &len);
    val = intwrap(val, -1, 255);
    if (!val)
    {
        return string;
    }

    randmax = (val < 0) ? 256 : (val * 2 + 1);
    srand((unsigned) time(NULL));

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            r = (int) data[0];
            g = (int) data[1];
            b = (int) data[2];

            if (colornoise)
            {
                if (val < 0)
                {
                    r = intwrap(rand() % randmax, 0, 255);
                    g = intwrap(rand() % randmax, 0, 255);
                    b = intwrap(rand() % randmax, 0, 255);
                }
                else
                {
                    r = intwrap(r + (rand() % randmax) - val, 0, 255);
                    g = intwrap(g + (rand() % randmax) - val, 0, 255);
                    b = intwrap(b + (rand() % randmax) - val, 0, 255);
                }
            }
            else
            {
                if (val < 0)
                {
                    i = intwrap(rand() % randmax, 0, 255);
                    r = i;
                    g = i;
                    b = i;
                }
                else
                {
                    i = (rand() % randmax) - val;
                    r = intwrap(r + i, 0, 255);
                    g = intwrap(g + i, 0, 255);
                    b = intwrap(b + i, 0, 255);
                }
            }
            outdata[0] = (unsigned char) r;
            outdata[1] = (unsigned char) g;
            outdata[2] = (unsigned char) b;
            outdata[3] = data[3];
            data += 4;
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
exchange_rgbcolor(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t len;
    int w, h, x, y;
    unsigned char *data, *outdata, *colormodel;
    unsigned char r, g, b;

    if (!PyArg_ParseTuple(args, "s#(ii)s", &data, &len, &w, &h, &colormodel))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &len);

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            r = data[0];
            g = data[1];
            b = data[2];

            if (!strcmp(colormodel, "gbr"))
            {
                outdata[0] = g;
                outdata[1] = b;
                outdata[2] = r;
            }
            else if (!strcmp(colormodel, "brg"))
            {
                outdata[0] = b;
                outdata[1] = r;
                outdata[2] = g;
            }
            else if (!strcmp(colormodel, "grb"))
            {
                outdata[0] = g;
                outdata[1] = r;
                outdata[2] = b;
            }
            else if (!strcmp(colormodel, "bgr"))
            {
                outdata[0] = b;
                outdata[1] = g;
                outdata[2] = r;
            } else
            {
                outdata[0] = r;
                outdata[1] = g;
                outdata[2] = b;
            }
            outdata[3] = data[3];
            data += 4;
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
to_sepiatone(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t len;
    int w, h, x, y, r, g, b, tone_r, tone_g, tone_b, bright;
    unsigned char *data, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)(iii)", &data, &len, &w, &h,
                &tone_r, &tone_g, &tone_b))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &len);

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            r = (int) data[0];
            g = (int) data[1];
            b = (int) data[2];
            bright = (r * 306 + g * 601 + b * 117) >> 10;
            r = intwrap(bright + tone_r, 0, 255);
            g = intwrap(bright + tone_g, 0, 255);
            b = intwrap(bright + tone_b, 0, 255);
            outdata[0] = (unsigned char) r;
            outdata[1] = (unsigned char) g;
            outdata[2] = (unsigned char) b;
            outdata[3] = data[3];
            data += 4;
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
spread_pixels(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t len;
    int w, h, x, y, x2, y2;
    unsigned char *data, *outdata;
    unsigned long idx;

    if (!PyArg_ParseTuple(args, "s#(ii)", &data, &len, &w, &h))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &len);
    srand((unsigned) time(NULL));

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            y2 = intwrap(y - (rand() % 5 + 2), 0, h - 1);
            x2 = intwrap(x - (rand() % 5 + 2), 0, w - 1);
            idx = (y2 * w + x2) * 4;
            outdata[0] = data[idx];
            outdata[1] = data[idx + 1];
            outdata[2] = data[idx + 2];
            outdata[3] = data[idx + 3];
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
filter(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t len;
    int r, g, b, w, h, x, y, wt[3][3], offset, div, i, i2, x2, y2;
    unsigned char *data, *outdata;
    unsigned long idx;

    if (!PyArg_ParseTuple(args, "s#(ii)((iii)(iii)(iii))ii",
                &data, &len, &w, &h,
                &wt[0][0], &wt[0][1], &wt[0][2], &wt[1][0], &wt[1][1],
                &wt[1][2], &wt[2][0], &wt[2][1], &wt[2][2], &offset, &div))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &len);

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            r = 0;
            g = 0;
            b = 0;

            for (i = 0; i < 3; i++)
            {
                for (i2 = 0; i2 < 3; i2++)
                {
                    y2 = intwrap(y + i - 1, 0, h - 1);
                    x2 = intwrap(x + i2 - 1, 0, w - 1);
                    idx = (y2 * w + x2) * 4;
                    r += data[idx] * wt[i][i2];
                    g += data[idx + 1] * wt[i][i2];
                    b += data[idx + 2] * wt[i][i2];
                }
            }
            r = intwrap(r / div + offset, 0, 255);
            g = intwrap(g / div + offset, 0, 255);
            b = intwrap(b / div + offset, 0, 255);
            outdata[0] = (unsigned char) r;
            outdata[1] = (unsigned char) g;
            outdata[2] = (unsigned char) b;
            outdata[3] = data[y * x * 4 + 3];
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
bordering(PyObject *self, PyObject *args)
{
    PyObject *points = NULL;
    size_t len;
    int w, h, x, y, r, g, b;
    unsigned char *data;
    unsigned char *data_lt, *data_mt, *data_rt, *data_lm, *data_rm, *data_lb, *data_mb, *data_rb;
    int find;

    if (!PyArg_ParseTuple(args, "s#(ii)", &data, &len, &w, &h))
        return NULL;

    points = PyList_New(0);
    if (!points)
        return NULL;

    data_lt = data - (w + 1) * 4;
    data_mt = data - w * 4;
    data_rt = data - (w - 1) * 4;
    data_lm = data - 4;
    data_rm = data + 4;
    data_lb = data + (w + 1) * 4;
    data_mb = data + w * 4;
    data_rb = data + (w - 1) * 4;
    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            if (data[3] != 0)
            {
                find = 0;
                find |= 0 < x && 0 < y && data_lt[3] == 0;
                find |= 0 < y && data_mt[3] == 0;
                find |= x + 1 < w && 0 < y && data_rt[3] == 0;
                find |= 0 < x && data_lm[3] == 0;
                find |= x + 1 < w && data_rm[3] == 0;
                find |= 0 < x && y + 1 < h && data_lb[3] == 0;
                find |= y + 1 < h && data_mb[3] == 0;
                find |= x + 1 < w && y + 1 < h && data_rb[3] == 0;

                if (find)
                {
                    PyList_Append(points, PyInt_FromSize_t(x));
                    PyList_Append(points, PyInt_FromSize_t(y));
                }
            }
            data += 4;
            data_lt += 4;
            data_mt += 4;
            data_rt += 4;
            data_lm += 4;
            data_rm += 4;
            data_lb += 4;
            data_mb += 4;
            data_rb += 4;
        }
    }
    return points;
}

static PyObject *
blend_add_1_50(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t dlen, slen;
    int w, h, x, y, dr, dg, db, sr, sg, sb, sa;
    unsigned char *dest, *source, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)s#", &dest, &dlen, &w, &h, &source, &slen))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, dlen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &dlen);

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            dr = (int) dest[0];
            dg = (int) dest[1];
            db = (int) dest[2];
            sr = (int) source[0];
            sg = (int) source[1];
            sb = (int) source[2];
            sa = (int) source[3];

            dr = colorwrap((dr * (255 - sa) >> 8) + (colorwrap(dr + sr) * sa >> 8));
            dg = colorwrap((dg * (255 - sa) >> 8) + (colorwrap(dg + sg) * sa >> 8));
            db = colorwrap((db * (255 - sa) >> 8) + (colorwrap(db + sb) * sa >> 8));

            outdata[0] = (char) dr;
            outdata[1] = (char) dg;
            outdata[2] = (char) db;

            source += 4;
            dest += 4;
            outdata += 4;
        }
    }
    return string;
}

#ifndef max
    #define max(a, b) ((a) > (b) ? (a) : (b))
#endif

static PyObject *
blend_sub_1_50(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    size_t dlen, slen;
    int w, h, x, y, dr, dg, db, sr, sg, sb, sa, a, b;
    unsigned char *dest, *source, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)s#", &dest, &dlen, &w, &h, &source, &slen))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, dlen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &dlen);

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            dr = (int) dest[0];
            dg = (int) dest[1];
            db = (int) dest[2];
            sr = (int) source[0];
            sg = (int) source[1];
            sb = (int) source[2];
            sa = (int) source[3];

            a = colorwrap(dr * (255 - sa) >> 8);
            b = colorwrap(dr - (sr * sa >> 8));
            dr = max(a, b);
            a = colorwrap(dg * (255 - sa) >> 8);
            b = colorwrap(dg - (sg * sa >> 8));
            dg = max(a, b);
            a = colorwrap(db * (255 - sa) >> 8);
            b = colorwrap(db - (sb * sa >> 8));
            db = max(a, b);

            outdata[0] = (char) dr;
            outdata[1] = (char) dg;
            outdata[2] = (char) db;

            source += 4;
            dest += 4;
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
to_disabledimage(PyObject *self, PyObject *args)
{
    size_t dlen;
    int px, w, h, keyR, keyG, keyB;
    Py_buffer buf;
    unsigned char *dest;
    static const int min = 140;
    static const int max = 240;

    if (!PyArg_ParseTuple(args, "s*(ii)", &buf, &w, &h))
        return NULL;

    dest = buf.buf;
    keyR = dest[0];
    keyG = dest[1];
    keyB = dest[2];
    for (px = 0; px + 3 <= buf.len; px += 3)
    {
        int r = dest[px+0];
        int g = dest[px+1];
        int b = dest[px+2];
        if (r == keyR && g == keyG && b == keyB)
        {
            continue;
        }
        dest[px+0] = r * (max - min) / 255  + min;
        dest[px+1] = g * (max - min) / 255  + min;
        dest[px+2] = b * (max - min) / 255  + min;
    }

    Py_RETURN_NONE;
}

#if defined(_WIN32) || defined(_WIN64)

#include <windows.h>

typedef struct FontInfo_ {
    HFONT hfont;
    HDC hdc;
    LPWSTR face;
    TEXTMETRIC tm;
    int pixels;
    BOOL bold;
    BOOL italic;
    BOOL underline;
} FontInfo;

static void _clear_font(FontInfo *font)
{
    if (font->hfont)
    {
        DeleteObject(font->hfont);
        font->hfont = NULL;
    }
    if (font->hdc)
    {
        DeleteDC(font->hdc);
        font->hdc = NULL;
    }
    memset(&font->tm, 0, sizeof(font->tm));
}

static void _font_del(FontInfo *font)
{
    HANDLE heap = GetProcessHeap();

    if (font)
    {
        _clear_font(font);
        if (font->face) HeapFree(heap, 0, font->face);
        HeapFree(heap, 0, font);
    }
}

static PyObject *
font_new(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;
    unsigned char *face;
    size_t facelen, bufSize;
    int pixels, bold, italic;
    HANDLE heap = GetProcessHeap();

    if (!PyArg_ParseTuple(args, "s#iii", &face, &facelen, &pixels, &bold, &italic))
        return NULL;

    font = (FontInfo*)HeapAlloc(heap, HEAP_ZERO_MEMORY, sizeof(FontInfo));
    if (!font) goto cleanup;

    bufSize = MultiByteToWideChar(CP_UTF8, 0, face, facelen, NULL, 0);
    font->face = (LPWSTR)HeapAlloc(heap, HEAP_ZERO_MEMORY, (bufSize+1) * sizeof(WCHAR));
    if (0 == MultiByteToWideChar(CP_UTF8, 0, face, facelen, font->face, bufSize)) goto cleanup;

    font->pixels = pixels;
    font->bold = bold;
    font->italic = italic;
    font->underline = FALSE;

    return Py_BuildValue("n", font);

cleanup:
    _font_del(font);

    return NULL;
}

static void _init_font(FontInfo *font)
{
    if (!font)
        return;

    _clear_font(font);

    font->hfont = CreateFontW(font->pixels, 0, 0, 0, font->bold ? FW_BOLD : FW_NORMAL, font->italic,
        font->underline, 0, DEFAULT_CHARSET, 0, 0, ANTIALIASED_QUALITY, 0, font->face);
    if (!font->hfont) goto cleanup;
    font->hdc = CreateCompatibleDC(NULL);
    if (!font->hdc) goto cleanup;
    if (!SelectObject(font->hdc, font->hfont)) goto cleanup;
    if (!GetTextMetrics(font->hdc, &font->tm)) goto cleanup;

    return;

cleanup:
    _clear_font(font);
}

static PyObject *
font_del(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;

    if (!PyArg_ParseTuple(args, "n", &font))
        return NULL;

    if (!font)
        return NULL;

    _font_del(font);

    Py_RETURN_NONE;
}

static PyObject *
font_bold(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;
    int val;

    if (!PyArg_ParseTuple(args, "ni", &font, &val))
        return NULL;

    if (!font)
        return NULL;

    if (font->bold != val)
        font->bold = val;
        _clear_font(font);

    Py_RETURN_NONE;
}

static PyObject *
font_italic(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;
    int val;

    if (!PyArg_ParseTuple(args, "ni", &font, &val))
        return NULL;

    if (!font)
        return NULL;

    if (font->italic != val)
        font->italic = val;
        _clear_font(font);

    Py_RETURN_NONE;
}

static PyObject *
font_underline(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;
    int val;

    if (!PyArg_ParseTuple(args, "ni", &font, &val))
        return NULL;

    if (!font)
        return NULL;

    if (font->underline != val)
        font->underline = val;
        _clear_font(font);

    Py_RETURN_NONE;
}

static PyObject *
font_height(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;

    if (!PyArg_ParseTuple(args, "n", &font))
        return NULL;

    if (!font)
        return NULL;

    if (!font->hdc)
        _init_font(font);

    return Py_BuildValue("i", font->tm.tmHeight);
}

static PyObject *
font_size(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;
    size_t utf8strlen = 0, bufSize = 0;
    unsigned char *utf8str = NULL;

    HANDLE heap = GetProcessHeap();
    LPWSTR str = NULL;
    GLYPHMETRICS gm = { 0 };
    MAT2 mat2 = { {0, 1}, {0, 0}, {0, 0}, {0, 1} };
    size_t i = 0, w = 0, w2 = 0, h = 0;
    UINT format = GGO_BITMAP;
    if (!PyArg_ParseTuple(args, "ns#", &font, &utf8str, &utf8strlen))
        return NULL;

    if (!utf8str || !font)
        return NULL;

    if (!font->hdc)
        _init_font(font);

    bufSize = MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, NULL, 0);
    str = HeapAlloc(heap, HEAP_ZERO_MEMORY, (bufSize+1) * sizeof(WCHAR));
    if (0 == MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, str, bufSize)) goto cleanup;

    h = font->tm.tmHeight;
    for (i = 0; str[i]; i++)
    {
        if (str[i] == '\n')
        {
            w = w2 < w ? w : w2;
            w2 = 0;
            h += font->tm.tmHeight;
            continue;
        }
        bufSize = GetGlyphOutlineW(font->hdc, str[i], format, &gm, 0, NULL, &mat2);
        w2 += gm.gmCellIncX;
    }
    w = w2 < w ? w : w2;

cleanup:
    if (str) HeapFree(heap, 0, str);

    return Py_BuildValue("(ii)", w, h);
}

static PyObject *
font_render(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    FontInfo *font = NULL;
    size_t utf8strlen = 0, bufSize = 0, outlen = 0;
    int r = 0, g = 0, b = 0, antialias = 0;
    unsigned char *outdata = NULL, *utf8str = NULL, *buf = NULL;

    HANDLE heap = GetProcessHeap();
    LPWSTR str = NULL;
    GLYPHMETRICS gm = { 0 };
    MAT2 mat2 = { {0, 1}, {0, 0}, {0, 0}, {0, 1} };
    size_t i = 0, w = 0, w2 = 0, h = 0, x = 0, y = 0, bpl = 0, xx = 0, yy = 0, p1 = 0, p2 = 0, x0 = 0, y0 = 0;
    unsigned char a = 0;
    UINT format = 0;

    if (!PyArg_ParseTuple(args, "ns#i(iii)", &font, &utf8str, &utf8strlen, &antialias, &r, &g, &b))
        return NULL;
    
    if (!utf8str || !font)
        return NULL;

    if (!font->hdc)
        _init_font(font);

    format = antialias ? GGO_GRAY8_BITMAP : GGO_BITMAP;

    bufSize = MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, NULL, 0);
    str = HeapAlloc(heap, HEAP_ZERO_MEMORY, (bufSize+1) * sizeof(WCHAR));
    if (0 == MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, str, bufSize)) goto cleanup;

    h = font->tm.tmHeight;
    for (i = 0; str[i]; i++)
    {
        if (str[i] == '\n')
        {
            w = w2 < w ? w : w2;
            w2 = 0;
            h += font->tm.tmHeight;
            continue;
        }
        bufSize = GetGlyphOutlineW(font->hdc, str[i], format, &gm, 0, NULL, &mat2);
        if (str[i+1])
        {
            w2 += gm.gmCellIncX;
        }
        else
        {
            w2 += max(gm.gmCellIncX, gm.gmptGlyphOrigin.x + gm.gmBlackBoxX);
        }
        h = max((int)h, (int)gm.gmptGlyphOrigin.y + (int)gm.gmBlackBoxY);
    }
    w = w2 < w ? w : w2;

    outlen = w * h * 4;
    string = PyBytes_FromStringAndSize(NULL, outlen);
    if (!string) goto cleanup;
    PyBytes_AsStringAndSize(string, (char**)&outdata, &outlen);
    memset(outdata, 0, outlen);

    for (i = 0; str[i]; i++)
    {
        if (str[i] == '\n')
        {
            x0 = 0;
            y0 += h;
            continue;
        }
        bufSize = GetGlyphOutlineW(font->hdc, str[i], format, &gm, 0, NULL, &mat2);
        buf = (unsigned char*)HeapAlloc(heap, HEAP_ZERO_MEMORY, bufSize);
        if (!iswspace(str[i]))
        {
            GetGlyphOutlineW(font->hdc, str[i], format, &gm, bufSize, buf, &mat2);
            x = x0 + gm.gmptGlyphOrigin.x;
            y = y0 + (font->tm.tmAscent - gm.gmptGlyphOrigin.y);
            if (antialias)
            {
                bpl = (gm.gmBlackBoxX + 3) / 4 * 4;
                for (xx = 0; xx < gm.gmBlackBoxX; xx++)
                {
                    if (w <= xx+x) continue;
                    for (yy = 0; yy < gm.gmBlackBoxY; yy++)
                    {
                        if (h <= yy+y) continue;
                        p1 = (yy * bpl) + xx;
                        a = buf[p1];
                        if (a)
                        {
                            p2 = (((y + yy) * w) + (x + xx)) * 4;
                            outdata[p2+0] = (unsigned char)r;
                            outdata[p2+1] = (unsigned char)g;
                            outdata[p2+2] = (unsigned char)b;
                            outdata[p2+3] = min(255, a*4);
                        }
                    }
                }
            }
            else
            {
                bpl = (gm.gmBlackBoxX + 31) / 32 * 4;
                for (xx = 0; xx < gm.gmBlackBoxX; xx++)
                {
                    if (w <= xx+x) continue;
                    for (yy = 0; yy < gm.gmBlackBoxY; yy++)
                    {
                        if (h <= yy+y) continue;
                        a = buf[bpl*yy+(xx/8)] & (1 << (7-(xx%8)));
                        if (a)
                        {
                            p2 = (((y + yy) * w) + (x + xx)) * 4;
                            outdata[p2+0] = (unsigned char)r;
                            outdata[p2+1] = (unsigned char)g;
                            outdata[p2+2] = (unsigned char)b;
                            outdata[p2+3] = a ? 255 : 0;
                        }
                    }
                }
            }
        }
        if (font->underline)
        {
            yy = y0 + font->tm.tmAscent;
            for (xx = 0; xx < x0 + gm.gmCellIncX; xx++)
            {
                p2 = ((yy * w) + xx) * 4;
                outdata[p2+0] = (unsigned char)r;
                outdata[p2+1] = (unsigned char)g;
                outdata[p2+2] = (unsigned char)b;
                outdata[p2+3] = 255;
            }
        }
        HeapFree(heap, 0, buf);
        x0 += gm.gmCellIncX;
    }

cleanup:
    if (str) HeapFree(heap, 0, str);

    return Py_BuildValue("O(ii)", string, w, h);
}

#endif

static PyMethodDef
_imageretouchMethods[] =
{
    {"add_mosaic", add_mosaic, METH_VARARGS,
        "add_mosaic(rgba_str, size, val)"},
    {"to_binaryformat", to_binaryformat, METH_VARARGS,
        "to_binaryformat(rgba_str, size, val, color)"},
    {"add_noise", add_noise, METH_VARARGS,
        "add_noise(rgba_str, size, val, colornoise=False)"},
    {"exchange_rgbcolor", exchange_rgbcolor, METH_VARARGS,
        "exchange_rgbcolor(rgba_str, size, colormodel)"},
    {"to_sepiatone", to_sepiatone, METH_VARARGS,
        "to_sepiatone(rgba_str, size, color)"},
    {"spread_pixels", spread_pixels, METH_VARARGS,
        "spread_pixels(rgba_str, size)"},
    {"filter", filter, METH_VARARGS,
        "filter(rgba_str, size, weight, offset, div)"},
    {"bordering", bordering, METH_VARARGS,
        "bordering(rgba_str, size)"},
    {"blend_add_1_50", blend_add_1_50, METH_VARARGS,
        "blend_add_1_50(rgba_str, size, rgba_str)"},
    {"blend_sub_1_50", blend_sub_1_50, METH_VARARGS,
        "blend_sub_1_50(rgba_str, size, rgba_str)"},
    {"to_disabledimage", to_disabledimage, METH_VARARGS,
        "to_disabledimage(char*, size)"},
#if defined(_WIN32) || defined(_WIN64)
    {"font_new", font_new, METH_VARARGS,
        "font_new(face, pixels, bold, italic)"},
    {"font_del", font_del, METH_VARARGS,
        "font_del(fontinfo)"},
    {"font_bold", font_bold, METH_VARARGS,
        "font_bold(fontinfo, val)"},
    {"font_italic", font_italic, METH_VARARGS,
        "font_italic(fontinfo, val)"},
    {"font_underline", font_underline, METH_VARARGS,
        "font_underline(fontinfo, val)"},
    {"font_height", font_height, METH_VARARGS,
        "font_height(fontinfo)"},
    {"font_size", font_size, METH_VARARGS,
        "font_size(fontinfo, text)"},
    {"font_render", font_render, METH_VARARGS,
        "font_render(fontinfo, text, antialias, color)"},
    {NULL, NULL, 0, NULL}
#endif
};

#ifdef __x86_64__
PyMODINIT_FUNC
init_imageretouch64(void)
{
    (void) Py_InitModule("_imageretouch64", _imageretouchMethods);
}
#else
PyMODINIT_FUNC
init_imageretouch32(void)
{
    (void) Py_InitModule("_imageretouch32", _imageretouchMethods);
}
#endif

