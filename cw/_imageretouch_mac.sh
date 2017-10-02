set -x
clang -shared _imageretouch.c -o_imageretouch_mac.so -I/usr/include/python2.7 -L/usr/include/python2.7 -fPIC -m64 -O3 -Wall -lpython2.7

