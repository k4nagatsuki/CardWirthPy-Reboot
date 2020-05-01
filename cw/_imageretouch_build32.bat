cl /LD /Ox /Fe"_imageretouch32.pyd" /I"C:\Program Files (x86)\Python38-32\include" /TC /nologo /WX /wd4820 /wd4100 /wd4255 /wd4668 /wd4115 /wd5045 /Wall _imageretouch.c /link gdi32.lib user32.lib /LIBPATH:"C:\Program Files (x86)\Python38-32\libs"
del _imageretouch32.exp
del _imageretouch32.lib
del _imageretouch.obj
