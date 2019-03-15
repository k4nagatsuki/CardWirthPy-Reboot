cl /LD /Ox /Fe"_imageretouch64.pyd" /I"C:\Program Files\Python36\include" /TC /nologo /WX /wd4820 /wd4100 /wd4255 /wd4668 /wd4115 /Wall _imageretouch.c /link gdi32.lib user32.lib /LIBPATH:"C:\Program Files\Python36\libs"
del _imageretouch64.exp
del _imageretouch64.lib
del _imageretouch.obj
