set -x
gcc -shared _imageretouch.c -o_imageretouch64.so -I/usr/include/python2.7 -L/usr/include/python2.7 -fPIC -m64 -O3 -Wall

