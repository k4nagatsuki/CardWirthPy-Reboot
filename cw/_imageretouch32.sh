set -x
gcc -shared _imageretouch.c -o_imageretouch32.so -I/usr/include/python3.5 -L/usr/include/python3.5 -fPIC -m32 -O3 -Wall

