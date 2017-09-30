#! /bin/sh

. common.sh

. bin/activate

wxpython_ARCHIVE=wxPython-src-3.0.2.0.tar.bz2
wxpython_DIR=$(echo $wxpython_ARCHIVE|sed 's/\.tar\.bz2$//')
wxpython_URLBASE="https://sourceforge.net/projects/wxpython/files/wxPython/3.0.2.0/"

### CREATE wxpython
fetch_archive   $wxpython_ARCHIVE $wxpython_URLBASE || exit 1
remove_builddir $wxpython_DIR
extract_archive $wxpython_ARCHIVE || exit 1
(
    cd_to_builddir $wxpython_DIR &&
    patch -p1 < "${PATCH_DIR}/wxpython-mac-gtk2.patch" &&
    patch -p1 < "${PATCH_DIR}/wxpython-clang.patch" &&

    export PKG_CONFIG_LIBDIR="${prefix}/lib/pkgconfig"
    export PKG_CONFIG_PATH="${prefix}/lib/pkgconfig:/opt/X11/lib/pkgconfig"
    export CPPFLAGS="-I${prefix}/include"
    export LDFLAGS="-L${prefix}/lib -Wl,-rpath,${prefix}/lib"

    cd wxPython &&
    python2.7 -u ./build-wxpython.py \
	      "--prefix=${prefix}" --unicode --mac_arch=`uname -m` --install
) || exit 1
