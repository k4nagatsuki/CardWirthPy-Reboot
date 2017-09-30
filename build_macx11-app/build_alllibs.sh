#! /bin/sh
if [ ! -f bin/activate ]; then
    ./init.sh
fi

# create common image libraries
./mk_imagelibs.sh   || exit 1

# create pygame with X11
./mk_sdl.sh         || exit 1
./mk_pygame.sh      || exit 1

# create wxpython with X11
./mk_gtk2.sh        || exit 1
./mk_wxpython.sh    || exit 1
