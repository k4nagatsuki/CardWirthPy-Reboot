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

    PyBytes_AsStringAndSize(string, &outdata, &len);
    val = intwrap(val, 0, 255);

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
    int w, h, x, y, val;
    unsigned char *data, *outdata, r, g, b;

    if (!PyArg_ParseTuple(args, "s#(ii)i", &data, &len, &w, &h, &val))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, &outdata, &len);
    val = intwrap(val, 0, 255);

    for (y = 0; y < h; y++)
    {
        for (x = 0; x < w; x++)
        {
            r = data[0];
            g = data[1];
            b = data[2];

            if (r <= val && g <= val && b <= val)
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

    PyBytes_AsStringAndSize(string, &outdata, &len);
    val = intwrap(val, -1, 255);
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
    unsigned char *data, *outdata, *colormodel, r, g, b;

    if (!PyArg_ParseTuple(args, "s#(ii)s", &data, &len, &w, &h, &colormodel))
        return NULL;

    string = PyBytes_FromStringAndSize(NULL, len);

    if (!string)
        return NULL;

    PyBytes_AsStringAndSize(string, &outdata, &len);

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

    PyBytes_AsStringAndSize(string, &outdata, &len);

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

    PyBytes_AsStringAndSize(string, &outdata, &len);
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

    PyBytes_AsStringAndSize(string, &outdata, &len);

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

static PyMethodDef
_imageretouchMethods[] =
{
    {"add_mosaic", add_mosaic, METH_VARARGS,
        "add_mosaic(rgba_str, size, val)"},
    {"to_binaryformat", to_binaryformat, METH_VARARGS,
        "to_binaryformat(rgba_str, size, val)"},
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
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
init_imageretouch(void)
{
    (void) Py_InitModule("_imageretouch", _imageretouchMethods);
}
