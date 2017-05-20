#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>
#include <math.h>
#include <time.h>

#if defined(_WIN32) || defined(_WIN64)
#   define inline __inline
#endif

static inline int
intwrap(int i, int min, int max)
{
    if (i > max)
        i = max;
    else if (i < min)
        i = min;

    return i;
}

#define colorwrap(i) intwrap(i, 0, 255)

static PyObject *
add_mosaic(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    Py_ssize_t len;
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
        memmove(outdata, data, len);
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
    Py_ssize_t len;
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
    Py_ssize_t len;
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
        memmove(outdata, data, len);
        return string;
    }

    randmax = (val < 0) ? 2 : (val * 2 + 1);
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
                    r = rand() % randmax ? 0 : 255;
                    g = rand() % randmax ? 0 : 255;
                    b = rand() % randmax ? 0 : 255;
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
                    i = rand() % randmax ? 0 : 255;
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
    Py_ssize_t len;
    int w, h, x, y;
    char *colormodel;
    unsigned char *data, *outdata;
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
    Py_ssize_t len;
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
    Py_ssize_t len;
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
    Py_ssize_t len;
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
            outdata[3] = data[(y*w + x) * 4 + 3];
            outdata += 4;
        }
    }
    return string;
}

static PyObject *
bordering(PyObject *self, PyObject *args)
{
    PyObject *points = NULL;
    Py_ssize_t len;
    int w, h, x, y;
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
    Py_ssize_t dlen, slen;
    int w, h, i, dr, dg, db, sr, sg, sb, sa;
    unsigned char *dest, *source, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)s#", &dest, &dlen, &w, &h, &source, &slen))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, dlen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &dlen);

    for (i = 0; i < w * h; i++)
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
    return string;
}

#ifndef max
    #define max(a, b) ((a) > (b) ? (a) : (b))
#endif

static PyObject *
blend_sub_1_50(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    Py_ssize_t dlen, slen;
    int w, h, i, dr, dg, db, sr, sg, sb, sa, a, b;
    unsigned char *dest, *source, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)s#", &dest, &dlen, &w, &h, &source, &slen))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, dlen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &dlen);

    for (i = 0; i < w * h; i++)
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
    return string;
}

static PyObject *
blend_mult_1_50(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    Py_ssize_t dlen, slen;
    int w, h, i, dr, dg, db, sr, sg, sb, sa;
    unsigned char *dest, *source, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)s#", &dest, &dlen, &w, &h, &source, &slen))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, dlen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &dlen);

    for (i = 0; i < w * h; i++)
    {
        dr = (int) dest[0];
        dg = (int) dest[1];
        db = (int) dest[2];
        sr = (int) source[0];
        sg = (int) source[1];
        sb = (int) source[2];
        sa = (int) source[3];

        if (sa != 255)
        {
            sr = colorwrap(((sr * sa) + (((1 << 8) - sa) << 8)) >> 8);
            sg = colorwrap(((sg * sa) + (((1 << 8) - sa) << 8)) >> 8);
            sb = colorwrap(((sb * sa) + (((1 << 8) - sa) << 8)) >> 8);
        }
        dr = colorwrap(dr * sr >> 8);
        dg = colorwrap(dg * sg >> 8);
        db = colorwrap(db * sb >> 8);

        outdata[0] = (char) dr;
        outdata[1] = (char) dg;
        outdata[2] = (char) db;

        source += 4;
        dest += 4;
        outdata += 4;
    }
    return string;
}

static PyObject *
blend_and(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    Py_ssize_t dlen, slen;
    int w, h, i, dr, dg, db, sr, sg, sb, mask_r, mask_g, mask_b;
    unsigned char *dest, *source, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)s#", &dest, &dlen, &w, &h, &source, &slen))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, dlen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &dlen);

    mask_r = (int) source[0];
    mask_g = (int) source[1];
    mask_b = (int) source[2];
    for (i = 0; i < w * h; i++)
    {
        dr = (int) dest[0];
        dg = (int) dest[1];
        db = (int) dest[2];
        sr = (int) source[0];
        sg = (int) source[1];
        sb = (int) source[2];
        if (sr != mask_r || sg != mask_g || sb != mask_b)
        {
            dr = dr & sr;
            dg = dg & sg;
            db = db & sb;
            outdata[0] = (char) dr;
            outdata[1] = (char) dg;
            outdata[2] = (char) db;
            outdata[3] = (unsigned char) 255;
        }
        else
        {
            outdata[0] = (char) dr;
            outdata[1] = (char) dg;
            outdata[2] = (char) db;
            outdata[3] = (unsigned char) 0;
        }

        source += 4;
        dest += 4;
        outdata += 4;
    }
    return string;
}

static PyObject *
blend_and_msg(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    Py_ssize_t dlen, slen;
    int w, h, i, dr, dg, db, sr, sg, sb, mask_r, mask_g, mask_b, base_r, base_g, base_b, base_a;
    unsigned char *dest, *source, *outdata;

    if (!PyArg_ParseTuple(args, "s#(ii)s#(iiii)", &dest, &dlen, &w, &h, &source, &slen, &base_r, &base_g, &base_b, &base_a))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, dlen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &dlen);

    mask_r = (int) source[0];
    mask_g = (int) source[1];
    mask_b = (int) source[2];
    for (i = 0; i < w * h; i++)
    {
        dr = (int) dest[0];
        dg = (int) dest[1];
        db = (int) dest[2];
        sr = (int) source[0];
        sg = (int) source[1];
        sb = (int) source[2];
        if (sr != mask_r || sg != mask_g || sb != mask_b)
        {
            dr = base_a & sr;
            dg = base_a & sg;
            db = base_a & sb;
            outdata[0] = (unsigned char) dr;
            outdata[1] = (unsigned char) dg;
            outdata[2] = (unsigned char) db;
            outdata[3] = (unsigned char) max(base_a, 255 - (sr + sg + sb) / 3);
        }
        else
        {
            outdata[0] = (char) dr;
            outdata[1] = (char) dg;
            outdata[2] = (char) db;
            outdata[3] = (unsigned char) 0;
        }

        source += 4;
        dest += 4;
        outdata += 4;
    }
    return string;
}

static PyObject *
to_disabledimage(PyObject *self, PyObject *args)
{
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
        dest[px+0] = (unsigned char)(r * (max - min) / 255 + min);
        dest[px+1] = (unsigned char)(g * (max - min) / 255 + min);
        dest[px+2] = (unsigned char)(b * (max - min) / 255 + min);
    }

    Py_RETURN_NONE;
}

static PyObject *
decode_rle4data(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    Py_ssize_t outlen, slen, si = 0, linepos = 0, x = 0, y = 0, pixels = 0, lines = 0, j = 0;
    int h, bpl;
    unsigned char count = 0, sb = 0;
    unsigned char *source, *outdata;

    if (!PyArg_ParseTuple(args, "s#ii", &source, &slen, &h, &bpl))
        return NULL;

    outlen = h * bpl;
    string = PyBytes_FromStringAndSize(NULL, outlen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &outlen);

    memset(outdata, 0, outlen);

#define GET_BYTE(b) {\
    if ((si & 1) == 1) si++;\
    if (slen <= si / 2)\
    {\
        /* PySys_WriteStdout("%d\n", __LINE__); */\
        goto exit_error;\
    }\
    b = source[si / 2];\
    si += 2;\
}
#define GET_PIXEL(b) {\
    if (slen <= si / 2)\
    {\
        /* PySys_WriteStdout("%d\n", __LINE__); */\
        goto exit_error;\
    }\
    if ((si & 1) == 0)\
    {\
        b = (source[si / 2] >> 4) & 0x0f;\
    }\
    else\
    {\
        b = source[si / 2] & 0x0f;\
    }\
    si++;\
}
#define PUT_PIXEL(b) {\
    if (outlen <= linepos + x / 2)\
    {\
        /* PySys_WriteStdout("%d\n", __LINE__); */\
        goto exit_error;\
    }\
    if ((x & 1) == 0)\
    {\
        outdata[linepos + x / 2] |= ((b) & 0x0f) << 4;\
    }\
    else\
    {\
        outdata[linepos + x / 2] |= (b) & 0x0f;\
    }\
    x++;\
}
    while (si < slen * 2)
    {
        GET_BYTE(count);
        if (count == 0)
        {
            GET_BYTE(count);
            switch (count)
            {
            case 0:
                /* EOL */
                x = 0;
                y++;
                linepos = y * bpl;
                break;
            case 1:
                /* EOB */
                si = slen * 2;
                break;
            case 2:
                /* Jump */
                GET_BYTE(pixels);
                GET_BYTE(lines);
                x += pixels;
                y += lines;
                linepos = y * bpl;
                break;
            default:
                /* Absolute Data */
                for (j = 0; j < count; j++)
                {
                    GET_PIXEL(sb);
                    PUT_PIXEL(sb);
                }
                if ((((count + 1) / 2) & 1) == 1) si += 2;
                break;
            }
        }
        else
        {
            /* Encoded Data */
            GET_BYTE(sb);
            for (j = 0; j < count; j++)
            {
                if ((j & 1) == 0)
                {
                    PUT_PIXEL((sb >> 4) & 0x0f);
                }
                else
                {
                    PUT_PIXEL(sb & 0x0f);
                }
            }
        }
    }

    return string;

exit_error:
    memset(outdata, 0, outlen);
    return string;
}

static PyObject *
has_alphabmp32(PyObject *self, PyObject *args)
{
    Py_ssize_t i, slen;
    unsigned char *source;

    if (!PyArg_ParseTuple(args, "s#", &source, &slen))
        return NULL;

    for (i = 0; i < slen; i += 4) {
        if (source[i + 3] != 0) {
            Py_RETURN_TRUE;
        }
    }

    Py_RETURN_FALSE;
}

static PyObject *
has_alpha(PyObject *self, PyObject *args)
{
    Py_ssize_t i, slen;
    unsigned char *source;

    if (!PyArg_ParseTuple(args, "s#", &source, &slen))
        return NULL;

    for (i = 0; i < slen; i += 4) {
        if (source[i + 3] != 255) {
            Py_RETURN_TRUE;
        }
    }

    Py_RETURN_FALSE;
}

static PyObject *
mul_alphaonly(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    Py_ssize_t slen, alpha, i;
    unsigned char *source, *outdata;
    double alnum;

    if (!PyArg_ParseTuple(args, "s#i", &source, &slen, &alpha))
        return NULL;

    alnum = alpha / 255.0;

    string = PyBytes_FromStringAndSize(NULL, slen);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, (char**)&outdata, &slen);

    for (i = 0; i < slen; i++)
    {
        outdata[i] = (char)(source[i] * alnum);
    }

    return string;
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

static inline void _clear_font(FontInfo *font)
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
    char *face;
    size_t facelen, bufSize;
    int pixels, bold, italic;
    HANDLE heap = GetProcessHeap();

    if (!PyArg_ParseTuple(args, "s#iii", &face, &facelen, &pixels, &bold, &italic))
        return NULL;

    font = (FontInfo*)HeapAlloc(heap, HEAP_ZERO_MEMORY, sizeof(FontInfo));
    if (!font)
    {
        PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "HeapAlloc", GetLastError());
        goto cleanup;
    }

    bufSize = MultiByteToWideChar(CP_UTF8, 0, face, facelen, NULL, 0);
    font->face = (LPWSTR)HeapAlloc(heap, HEAP_ZERO_MEMORY, (bufSize+1) * sizeof(WCHAR));
    if (bufSize)
    {
        if (0 == MultiByteToWideChar(CP_UTF8, 0, face, facelen, font->face, bufSize))
        {
            PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "MultiByteToWideChar", GetLastError());
            goto cleanup;
        }
    }

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
    if (!font->hfont)
    {
        PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "CreateFontW", GetLastError());
        goto cleanup;
    }
    font->hdc = CreateCompatibleDC(NULL);
    if (!font->hdc)
    {
        PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "CreateCompatibleDC", GetLastError());
        goto cleanup;
    }
    if (!SelectObject(font->hdc, font->hfont))
    {
        PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "SelectObject", GetLastError());
        goto cleanup;
    }
    if (!GetTextMetrics(font->hdc, &font->tm))
    {
        PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "GetTextMetrics", GetLastError());
        goto cleanup;
    }

    if (CLR_INVALID == SetTextColor(font->hdc, RGB(255, 255, 255)))
    {
        PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "SetTextColor", GetLastError());
        goto cleanup;
    }
    if (!SetBkMode(font->hdc, TRANSPARENT))
    {
        PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "SetBkMode", GetLastError());
        goto cleanup;
    }

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
    {
        font->bold = val;
        _clear_font(font);
    }

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
    {
        font->italic = val;
        _clear_font(font);
    }

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
    {
        font->underline = val;
        _clear_font(font);
    }

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

static void _get_imagesize(FontInfo *font, LPWSTR str, size_t bufSize, size_t *rw, size_t *rh)
{
    SIZE size = { 0 };
    ABC width = { 0 };

    *rw = 1;
    *rh = 1;

    if (0 == GetTextExtentPoint32W(font->hdc, str, bufSize, &size)) goto cleanup;

    if (font->italic && 1 <= bufSize)
    {
        if (!GetCharABCWidths(font->hdc, str[bufSize - 1], str[bufSize - 1], &width)) goto cleanup;
        size.cx += abs(width.abcA);
        size.cx += abs(width.abcC);
    }

cleanup:
    *rw = max(1, size.cx);
    *rh = max(1, size.cy);
}

static PyObject *
font_size(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;
    size_t utf8strlen = 0, bufSize = 0;
    char *utf8str = NULL;
    SIZE size = { 0 };

    HANDLE heap = GetProcessHeap();
    LPWSTR str = NULL;

    if (!PyArg_ParseTuple(args, "ns#", &font, &utf8str, &utf8strlen))
        return NULL;

    if (!utf8str || !font)
        return NULL;

    if (!font->hdc)
        _init_font(font);

    bufSize = MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, NULL, 0);
    str = HeapAlloc(heap, HEAP_ZERO_MEMORY, (bufSize+1) * sizeof(WCHAR));
    if (bufSize)
    {
        if (0 == MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, str, bufSize)) goto cleanup;
    }

    if (0 == GetTextExtentPoint32W(font->hdc, str, bufSize, &size)) goto cleanup;

cleanup:
    if (str) HeapFree(heap, 0, str);

    return Py_BuildValue("(ii)", size.cx, size.cy);
}

static PyObject *
font_render(PyObject *self, PyObject *args)
{
    PyObject *string = NULL;
    FontInfo *font = NULL;
    Py_ssize_t utf8strlen = 0, bufSize = 0, outlen = 0;
    int r = 0, g = 0, b = 0, antialias = 0;
    size_t w = 0, h = 0;
    unsigned char *outdata = NULL;
    char *utf8str = NULL;

    HANDLE heap = GetProcessHeap();
    LPWSTR str = NULL;
    BITMAPINFO info = { 0 };
    HBITMAP bitmap = NULL, oldBitmap = NULL;
    unsigned char *pixels = NULL;
    Py_ssize_t i = 0;

    if (!PyArg_ParseTuple(args, "ns#i(iii)", &font, &utf8str, &utf8strlen, &antialias, &r, &g, &b))
    {
        PySys_WriteStderr("%s(%d): %s\n", __FILE__, __LINE__, "PyArg_ParseTuple");
        return NULL;
    }

    if (!utf8str || !font)
    {
        PySys_WriteStderr("%s(%d): %s\n", __FILE__, __LINE__, "NoText or NoFont");
        return NULL;
    }

    if (!font->hdc)
        _init_font(font);

    bufSize = MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, NULL, 0);
    if (bufSize)
    {
        str = HeapAlloc(heap, HEAP_ZERO_MEMORY, (bufSize+1) * sizeof(WCHAR));
        if (0 == MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, str, bufSize))
        {
            PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "MultiByteToWideChar", GetLastError());
            goto cleanup;
        }
    }

    if (bufSize == 0)
    {
        outlen = 4;
        string = PyBytes_FromStringAndSize(NULL, outlen);
        if (!string)
        {
            PySys_WriteStderr("%s(%d): %s\n", __FILE__, __LINE__, "PyBytes_FromStringAndSize");
            goto cleanup;
        }
        PyBytes_AsStringAndSize(string, (char**)&outdata, &outlen);
        memset(outdata, 0, outlen);
    }
    else
    {
        _get_imagesize(font, str, bufSize, &w, &h);

        info.bmiHeader.biSize = sizeof(info);
        info.bmiHeader.biWidth = w;
        info.bmiHeader.biHeight = -(LONG)h;
        info.bmiHeader.biPlanes = 1;
        info.bmiHeader.biBitCount = 32;
        info.bmiHeader.biCompression = 0;
        bitmap = CreateDIBSection(0, &info, DIB_RGB_COLORS, (void**)&pixels, 0, 0);
        if (!bitmap)
        {
            PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "CreateDIBSection", GetLastError());
            goto cleanup;
        }
        oldBitmap = (HBITMAP)SelectObject(font->hdc, bitmap);

        if (!TabbedTextOutW(font->hdc, 0, 0, str, bufSize, 0, NULL, 0))
        {
            PySys_WriteStderr("%s(%d): %s, ErrCode: %d\n", __FILE__, __LINE__, "TabbedTextOutW", GetLastError());
            goto cleanup;
        }

        outlen = w * h * 4;
        string = PyBytes_FromStringAndSize(NULL, outlen);
        if (!string)
        {
            PySys_WriteStderr("%s(%d): %s\n", __FILE__, __LINE__, "PyBytes_FromStringAndSize");
            goto cleanup;
        }
        PyBytes_AsStringAndSize(string, (char**)&outdata, &outlen);
        memset(outdata, 0, outlen);

        for (i = 0; i < (LONG)(w * h * 4); i += 4)
        {
            outdata[i+0] = (unsigned char)r;
            outdata[i+1] = (unsigned char)g;
            outdata[i+2] = (unsigned char)b;
            outdata[i+3] = pixels[i];
        }
    }

cleanup:
    if (str) HeapFree(heap, 0, str);
    if (oldBitmap) SelectObject(font->hdc, oldBitmap);
    if (bitmap) DeleteObject(bitmap);

    /* BUG: If returned a tuple here, GC doesn't correct this string.
            Therefore, Returns only string here.
            And Created font_imagesize for getting (w, h). */
    /*return Py_BuildValue("s(ii)", string, w, h);*/
    return string;
}

static PyObject *
font_imagesize(PyObject *self, PyObject *args)
{
    FontInfo *font = NULL;
    size_t utf8strlen = 0, bufSize = 0;
    int antialias = 0;
    char *utf8str = NULL;

    HANDLE heap = GetProcessHeap();
    LPWSTR str = NULL;
    size_t w = 0, h = 0;

    if (!PyArg_ParseTuple(args, "ns#i", &font, &utf8str, &utf8strlen, &antialias))
        return NULL;

    if (!utf8str || !font)
        return NULL;

    if (!font->hdc)
        _init_font(font);

    bufSize = MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, NULL, 0);
    str = HeapAlloc(heap, HEAP_ZERO_MEMORY, (bufSize+1) * sizeof(WCHAR));
    if (bufSize)
    {
        if (0 == MultiByteToWideChar(CP_UTF8, 0, utf8str, utf8strlen, str, bufSize)) goto cleanup;
        _get_imagesize(font, str, bufSize, &w, &h);
    }
    else
    {
        w = 1;
        h = 1;
    }

cleanup:
    if (str) HeapFree(heap, 0, str);

    return Py_BuildValue("(ii)", w, h);
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
    {"blend_mult_1_50", blend_mult_1_50, METH_VARARGS,
        "blend_mult_1_50(rgba_str, size, rgba_str)"},
    {"blend_and", blend_and, METH_VARARGS,
        "blend_and(rgba_str, size, rgba_str)"},
    {"blend_and_msg", blend_and_msg, METH_VARARGS,
        "blend_and_msg(rgba_str, size, rgba_str, rgba)"},
    {"to_disabledimage", to_disabledimage, METH_VARARGS,
        "to_disabledimage(char*, size)"},
    {"decode_rle4data", decode_rle4data, METH_VARARGS,
        "decode_rle4data(char*, h, bpl)"},
    {"has_alphabmp32", has_alphabmp32, METH_VARARGS,
        "has_alphabmp32(char*)"},
    {"has_alpha", has_alpha, METH_VARARGS,
        "has_alpha(char*)"},
    {"mul_alphaonly", mul_alphaonly, METH_VARARGS,
        "mul_alphaonly(a_str, alpha)"},
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
    {"font_imagesize", font_imagesize, METH_VARARGS,
        "font_imagesize(fontinfo, text, antialias)"},
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
