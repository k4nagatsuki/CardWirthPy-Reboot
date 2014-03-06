set -x
gcc -shared _imageretouch.c -o_imageretouch.so -I/usr/include/python2.7 -L/usr/include/python2.7 -fPIC

