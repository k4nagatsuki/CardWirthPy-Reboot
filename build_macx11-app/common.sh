#! /bin/sh

prefix=`pwd`

BUILD_DIR="${prefix}/../build"
ARCHIVE_DIR="${prefix}/archives"
HASH_DIR="${prefix}/hash"
PATCH_DIR="${prefix}/patches"

export CXX="g++ -stdlib=libstdc++"
export CFLAGS="-mmacosx-version-min=10.7 -O3"
export CXXFLAGS="-mmacosx-version-min=10.7 -O3"

fetch_archive() {
    archive="$1"
    url_base="$2"
    [ -d "$ARCHIVE_DIR" ] || mkdir -p "$ARCHIVE_DIR"
    check_archive "$archive" && return 0
    rm -f "$ARCHIVE_DIR/$archive"
    curl -L -o "$ARCHIVE_DIR/$archive" "$url_base/$archive" 
    check_archive "$archive" || exit 1
}

fetch_archive_by_pip() {
    outvar="$1"
    package="$2"
    version="$3"
    if [ x"$version" != x"" ]; then
	pkgver="$package==$version"
    else
	pkgver="$package"
    fi
    
    [ -d "$ARCHIVE_DIR" ] || mkdir -p "$ARCHIVE_DIR"
    pip download --no-binary :all: -d "$ARCHIVE_DIR" "$pkgver" || exit 1
    archive=$(cd "$ARCHIVE_DIR" && ls -1 | grep -ie "${package}-.*\\.tar\\.gz" | tail -1)
    if [ -z "$archive" ]; then
	print "Getint archive name is failed"
	exit 1
    fi
    eval "$outvar=$archive"
}

check_archive() {
    archive="$1"
    file="$ARCHIVE_DIR/$archive"
    hash="$HASH_DIR/${archive}.sha1"
    if [ ! -r "$file" ]; then
	return 1
    fi
    if [ ! -r "$hash" ]; then
	echo "WARN: hash of $archive is not found"
	return 0
    fi
    tmpfile="/tmp/hash_check.$$"
    shasum "$file" | awk '{ print $1 }' > "$tmpfile"
    if diff "$hash" "$tmpfile" 2>&1 > /dev/null; then
	ret=0
    else
	echo "ARCHIVE $archive is broken"
	ret=1
    fi
    rm -f "$tmpfile"
    return $ret
}

remove_builddir() {
    [ -d "$BUILD_DIR/$1" ] && rm -rf "$BUILD_DIR/$1"
}

cd_to_builddir() {
    cd "$BUILD_DIR/$1"
}

extract_archive() {
    archive="$1"
    check_archive "$archive" || (echo "Archive $archive is not found"; return 1)
    file="$ARCHIVE_DIR/$archive"
    [ -d "$BUILD_DIR" ] || mkdir "$BUILD_DIR"
    case "$file" in
	*.tar.gz)
	    tar zxvf "$file" -C "$BUILD_DIR"
	    ;;
	*.tar.bz2)
	    tar jxvf "$file" -C "$BUILD_DIR"
	    ;;
	*.tar.xz)
	    tar Jxvf "$file" -C "$BUILD_DIR"
	    ;;
	*.zip)
	    (cd "$BUILD_DIR" && unzip "$file")
	    ;;
	*)
	    echo "UNKOWN format $archive"
	    return 1
    esac
}
