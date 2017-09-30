#! /bin/sh

. common.sh

SDL_ARCHIVE=SDL-1.2.15.tar.gz
SDL_DIR=$(echo $SDL_ARCHIVE|sed 's/\.tar\.gz$//')
SDL_URLBASE="https://www.libsdl.org/release/"

SDL_ttf_ARCHIVE=SDL_ttf-2.0.11.tar.gz
SDL_ttf_DIR=$(echo $SDL_ttf_ARCHIVE|sed 's/\.tar\.gz$//')
SDL_ttf_URLBASE="https://www.libsdl.org/projects/SDL_ttf/release/"

SDL_image_ARCHIVE=SDL_image-1.2.12.tar.gz
SDL_image_DIR=$(echo $SDL_image_ARCHIVE|sed 's/\.tar\.gz$//')
SDL_image_URLBASE="https://www.libsdl.org/projects/SDL_image/release/"

SDL_mixer_ARCHIVE=SDL_mixer-1.2.12.tar.gz
SDL_mixer_DIR=$(echo $SDL_mixer_ARCHIVE|sed 's/\.tar\.gz$//')
SDL_mixer_URLBASE="https://www.libsdl.org/projects/SDL_mixer/release/"

export PKG_CONFIG_LIBDIR="${prefix}/lib/pkgconfig"
export PKG_CONFIG_PATH="${prefix}/lib/pkgconfig:/opt/X11/lib/pkgconfig"

### CREATE SDL
fetch_archive   $SDL_ARCHIVE $SDL_URLBASE || exit 1
remove_builddir $SDL_DIR
extract_archive $SDL_ARCHIVE || exit 1
(
    cd_to_builddir $SDL_DIR &&
    patch -p1 < "${PATCH_DIR}/libsdl-1.2.15-const-xdata32.patch" &&
    patch -p1 < "${PATCH_DIR}/libsdl-1.2.15-without-macframework.patch" &&
    ./autogen.sh &&
    ./configure \
	"--prefix=${prefix}" \
	--disable-video-cocoa \
	--disable-video-carbon \
	--disable-joystick \
	--disable-cdrom \
	--with-x \
	--enable-video-x11 &&
    make && make install
) || exit 1

### CREATE SDL_ttf
fetch_archive   $SDL_ttf_ARCHIVE $SDL_ttf_URLBASE || exit 1
remove_builddir $SDL_ttf_DIR
extract_archive $SDL_ttf_ARCHIVE || exit 1
(
    cd_to_builddir $SDL_ttf_DIR &&
    ./configure \
	"--prefix=${prefix}" \
	--with-freetype-prefix=/opt/X11 \
	"--with-sdl-prefix=${prefix}" && 
    make && make install
) || exit 1

### CREATE SDL_image
fetch_archive   $SDL_image_ARCHIVE $SDL_image_URLBASE || exit 1
remove_builddir $SDL_image_DIR
extract_archive $SDL_image_ARCHIVE || exit 1
(
    cd_to_builddir $SDL_image_DIR &&
    ./configure \
	"--prefix=${prefix}" \
	"--with-sdl-prefix=${prefix}" \
	--disable-jpg-shared \
	--disable-png-shared \
	--disable-tif-shared \
	--disable-imageio \
	--disable-webp \
	--disable-webp-shared \
	CPPFLAGS="-I${prefix}/include" \
	LDFLAGS="-L${prefix}/lib" &&
    make && make install
) || exit 1

### CREATE libSDL_mixer
fetch_archive   $SDL_mixer_ARCHIVE $SDL_mixer_URLBASE || exit 1
remove_builddir $SDL_mixer_DIR
extract_archive $SDL_mixer_ARCHIVE || exit 1
(
    cd_to_builddir $SDL_mixer_DIR &&
    ./configure \
	"--prefix=${prefix}" \
	"--with-sdl-prefix=${prefix}" \
	--disable-music-mod \
	--disable-music-mod-shared \
	--disable-music-mod-modplug \
	--disable-music-midi \
	--disable-music-timidity-midi \
	--disable-music-native-midi \
	--disable-music-fluidsynth-midi \
	--disable-music-fluidsynth-shared \
	--disable-music-ogg \
	--disable-music-ogg-shared \
	--disable-music-flac \
	--disable-music-flac-shared \
	--disable-music-mp3 \
	--disable-music-mp3-shared \
	CPPFLAGS="-I${prefix}/include" \
	LDFLAGS="-L${prefix}/lib" &&
    make && make install
) || exit 1
