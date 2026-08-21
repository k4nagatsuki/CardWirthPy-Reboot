cl /LD /Ox /Fe"_imageretouch64.pyd" /I"C:\Users\user\AppData\Local\Programs\Python\Python313\Include" /TC /nologo /WX /wd4820 /wd4100 /wd4255 /wd4668 /wd4115 /wd4711 /Wall _imageretouch.c /link gdi32.lib user32.lib /LIBPATH:"C:\Users\user\AppData\Local\Programs\Python\Python313\libs"
del _imageretouch64.exp
del _imageretouch64.lib
del _imageretouch.obj
