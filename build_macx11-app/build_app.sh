#! /bin/sh

prefix=`pwd`
. bin/activate

clang -Wall -Werror -Wno-deprecated-declarations \
      `python2.7-config --cflags --ldflags` \
      -o bundle_main bundle_main.c || exit 1

cd ..
python2.7 "${prefix}/build_macapp-x11.py"
