#! /bin/sh

APP="../CardWirthPy.app"
DOCS="../ReadMe.txt ../ChangeLog.txt LICENSE_mac.txt README_mac.md install_font.command"
WORKDIR=`pwd`/dmg_work
HGTMPDIR=`pwd`/tmp

if [ ! -d "$APP" ]; then
    echo "Please build CardWirthPy.app at first."
    exit 1
fi

VERSION=$(grep -A 1 CFBundleVersion "$APP/Contents/Info.plist" | grep -v CFBundleVersion | sed -e 's/^[^>]*>\([^<]*\)<.*$/\1/')
if [ -z "$1" ]; then
    VERSION="${VERSION}-$(date '+%Y%m%d')"
else
    VERSION="$1"
fi

mkdir "$WORKDIR" || exit 1

# TEMPORARY CHECKOUT
rm -rf "$HGTMPDIR"
hg clone .. "$HGTMPDIR"
cp -RpH "$HGTMPDIR/Data" "$WORKDIR"

cp -RpH "$APP" "$WORKDIR"
for f in $DOCS; do
    cp -p "$f" "$WORKDIR/$(basename "$f"|sed 's/\.md$/.txt/')"
done

ARCNAME="CardWirthPy-${VERSION}"
hdiutil create \
	-srcfolder "$WORKDIR" \
	-volname "$ARCNAME" \
	-fs HFS+ \
	-format UDBZ \
	"${ARCNAME}.dmg"
rm -rf "$WORKDIR" "$HGTMPDIR"
