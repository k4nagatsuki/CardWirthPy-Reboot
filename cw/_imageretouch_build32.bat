cl /LD /Ox /Fe"_imageretouch32.pyd" /I"C:\Python27\include" /TC /nologo /WX /wd4820 /wd4100 /wd4255 /wd4668 /Wall _imageretouch.c /link gdi32.lib user32.lib /LIBPATH:"C:\Python27\libs"
del _imageretouch32.exp
del _imageretouch32.lib
del _imageretouch.obj
