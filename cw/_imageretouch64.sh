set -x
gcc -shared _imageretouch.c -o_imageretouch64.so -I/usr/include/python3.6 -L/usr/include/python3.6 -fPIC -m64 -O3 -Wall

