#! /bin/sh

. common.sh

. ./bin/activate

export SDL_CONFIG="${prefix}/bin/sdl-config"
export FREETYPE_CONFIG=/opt/X11/bin/freetype-config
export LOCALBASE="${prefix}"

fetch_archive_by_pip PYGAME_ARCHIVE pygame
PYGAME_DIR=$(echo $PYGAME_ARCHIVE|sed 's/\.tar\.gz$//')

remove_builddir $PYGAME_DIR
extract_archive $PYGAME_ARCHIVE
(
    cd_to_builddir $PYGAME_DIR &&
    patch -p1 < "${PATCH_DIR}/pygame-without-cocoa-carbon.patch" &&
    patch -p1 < "${PATCH_DIR}/pygame-disable-joystick.patch" &&
    python config.py -auto &&
    python setup.py build &&
    python setup.py install --optimize=1
) || exit 1
