#! /bin/sh

. common.sh

LIBJPEG_ARCHIVE=jpegsrc.v9b.tar.gz
LIBJPEG_DIR=jpeg-9b
LIBJPEG_URLBASE="http://www.ijg.org/files/"

LIBPNG_ARCHIVE=libpng-1.6.32.tar.xz
LIBPNG_DIR=$(echo $LIBPNG_ARCHIVE|sed 's/\.tar\.xz$//')
LIBPNG_URLBASE="http://prdownloads.sourceforge.net/libpng/"

# REMOVE JBIGKIT, because it is licensed by GPL
#JBIGKIT_ARCHIVE=jbigkit-2.1.tar.gz
#JBIGKIT_DIR=$(echo $JBIGKIT_ARCHIVE|sed 's/\.tar\.gz$//')
#JBIGKIT_URLBASE="http://www.cl.cam.ac.uk/~mgk25/jbigkit/download/"

TIFF_ARCHIVE=tiff-4.0.8.tar.gz
TIFF_DIR=$(echo $TIFF_ARCHIVE|sed 's/\.tar\.gz$//')
TIFF_URLBASE="ftp://download.osgeo.org/libtiff/"

### CREATE libjpeg
fetch_archive   $LIBJPEG_ARCHIVE $LIBJPEG_URLBASE || exit 1
remove_builddir $LIBJPEG_DIR
extract_archive $LIBJPEG_ARCHIVE || exit 1
(
    cd_to_builddir $LIBJPEG_DIR &&
    ./configure \
	"--prefix=${prefix}" &&
    make && make install
) || exit 1

### CREATE libpng
fetch_archive   $LIBPNG_ARCHIVE $LIBPNG_URLBASE || exit 1
remove_builddir $LIBPNG_DIR
extract_archive $LIBPNG_ARCHIVE || exit 1
(
    cd_to_builddir $LIBPNG_DIR &&
    patch -p1 < "${PATCH_DIR}/libpng-nozlib.patch" &&
    ./configure \
	"--prefix=${prefix}" &&
    make && make install
) || exit 1

#### CREATE JBIGKIT for TIFF
#fetch_archive   $JBIGKIT_ARCHIVE $JBIGKIT_URLBASE || exit 1
#remove_builddir $JBIGKIT_DIR
#extract_archive $JBIGKIT_ARCHIVE || exit 1
#(
#    cd_to_builddir $JBIGKIT_DIR &&
#    make lib &&
#    cp libjbig/*.a "${prefix}/lib" && cp libjbig/*.h "${prefix}/include"
#) || exit 1

### CREATE tiff
fetch_archive   $TIFF_ARCHIVE $TIFF_URLBASE || exit 1
remove_builddir $TIFF_DIR
extract_archive $TIFF_ARCHIVE || exit 1
(
    cd_to_builddir $TIFF_DIR &&
    ./configure \
	"--prefix=${prefix}" \
	--without-x \
	CPPFLAGS="-I${prefix}/include" \
	LDFLAGS="-L${prefix}/lib"
    make && make install
) || exit 1
