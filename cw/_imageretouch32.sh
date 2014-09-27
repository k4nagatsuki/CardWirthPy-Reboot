set -x
gcc -shared _imageretouch.c -o_imageretouch32.so -I/usr/include/python2.7 -L/usr/include/python2.7 -fPIC -m32

