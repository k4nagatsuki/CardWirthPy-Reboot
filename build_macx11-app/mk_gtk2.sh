#! /bin/sh

. common.sh

gettext_ARCHIVE=gettext-0.19.8.1.tar.xz
gettext_URLBASE="https://ftp.gnu.org/pub/gnu/gettext/"

glib2_ARCHIVE=glib-2.54.0.tar.xz
glib2_URLBASE="https://ftp.gnome.org/pub/gnome/sources/glib/2.54/"

# cairo is already installed by XQuartz
#cairo_ARCHIVE=cairo-1.14.10.tar.xz
#cairo_URLBASE="https://www.cairographics.org/releases/"

harfbuzz_ARCHIVE=harfbuzz-1.5.1.tar.bz2
harfbuzz_URLBASE="https://www.freedesktop.org/software/harfbuzz/release/"

pango_ARCHIVE=pango-1.40.12.tar.xz
pango_URLBASE="http://ftp.gnome.org/pub/gnome/sources/pango/1.40/"

atk_ARCHIVE=atk-2.24.0.tar.xz
atk_URLBASE="http://ftp.gnome.org/pub/gnome/sources/atk/2.24/"

gdk_pixbuf_ARCHIVE=gdk-pixbuf-2.36.10.tar.xz
gdk_pixbuf_URLBASE="http://ftp.gnome.org/pub/gnome/sources/gdk-pixbuf/2.36/"

gtk2_ARCHIVE=gtk+-2.24.31.tar.xz
gtk2_URLBASE="http://ftp.gnome.org/pub/gnome/sources/gtk+/2.24/"

#glib2_patch_URL="https://raw.githubusercontent.com/macports/macports-ports/master/devel/glib2/files"
glib2_patch_URL="https://raw.githubusercontent.com/macports/macports-ports/7aa30b3379a744aa37d97ec465aeedb3bb056f2b/devel/glib2/files"
glib2_patches=
glib2_patches="$glib2_patches patch-glib-gmain.c.diff"
glib2_patches="$glib2_patches patch-glib_gunicollate.c.diff"
glib2_patches="$glib2_patches patch-configure-switch-for-gappinfo-impl-mp.diff"


libs="gettext glib2 harfbuzz pango atk gdk_pixbuf gtk2"

for l in $libs; do
    eval "archive=\$${l}_ARCHIVE"
    eval "urlbase=\$${l}_URLBASE"
    dir=$(echo $archive|sed -E 's/\.tar\.(gz|bz2|xz)$//')

    fetch_archive   $archive $urlbase || exit 1
    remove_builddir $dir
    extract_archive $archive || exit 1

    case $l in
	gettext)
	    (
		cd_to_builddir $dir &&
		patch -p1 < "${PATCH_DIR}/gettext-use-system-localedir.patch"
	    ) || exit 1
	    configure_args="--disable-java --disable-native-java --disable-csharp --without-emacs"
	    ;;
	glib2)
	    [ -d "${BUILD_DIR}/glib2_patches" ] \
		|| mkdir -p "${BUILD_DIR}/glib2_patches"
	    (
		cd "${BUILD_DIR}/glib2_patches" &&
		for p in $glib2_patches; do
		    if [ ! -f "$p" ]; then
			curl -LO "${glib2_patch_URL}/$p"
		    fi
		done
	    ) || exit 1
	    (
		cd_to_builddir $dir &&
		cat "${BUILD_DIR}"/glib2_patches/*.diff | patch -p0 &&
		patch -p1 < "${PATCH_DIR}/glib-disable-giomodule.patch"
		patch -p1 < "${PATCH_DIR}/glib-fdopendir-check.patch"
	    ) || exit 1
	    configure_args="--with-appinfo-impl=generic --with-pcre=internal LIBFFI_CFLAGS=-I/usr/include/ffi LIBFFI_LIBS=-lffi"
	    ;;
	harfbuzz)
	    configure_args="--with-cairo=yes --with-icu=no --with-coretext=no"
	    ;;
	gdk_pixbuf)
	    configure_args="--disable-modules --with-included-loaders=yes --with-x11 LIBJPEG=-ljpeg LIBTIFF=-ltiff"
	    ;;
	gtk2)
	    configure_args="--disable-modules --with-xinput --with-included-immodules=xim --with-x --with-gdktarget=x11"
	    # quick & dirty hack
	    [ -d "${prefix}/lib/gtk-2.0/2.10.0" ] \
		|| mkdir -p "${prefix}/lib/gtk-2.0/2.10.0"
	    ;;
	*)
	    configure_args=
	    ;;
    esac

    export PKG_CONFIG_LIBDIR="${prefix}/lib/pkgconfig"
    export PKG_CONFIG_PATH="${prefix}/lib/pkgconfig:/opt/X11/lib/pkgconfig"
    (
	cd_to_builddir $dir &&
	./configure \
	    "--prefix=${prefix}" $configure_args \
	    CPPFLAGS="-I${prefix}/include" \
	    LDFLAGS="-L${prefix}/lib" &&
	make && make install
    ) || exit 1
done
