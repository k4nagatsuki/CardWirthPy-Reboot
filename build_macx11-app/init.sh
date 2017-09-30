#! /bin/sh

. common.sh

virtualenv --python=/usr/bin/python2.7 ${prefix}
. "${prefix}/bin/activate"
pip install py2app || exit 1

LHAFILE_ARCHIVE=lhafile-0.1.tar.gz
LHAFILE_DIR=$(echo $LHAFILE_ARCHIVE|sed 's/\.tar\.gz$//')
LHAFILE_URLBASE="https://trac.neotitans.net/wiki/lhafile/"

### install lhafile
fetch_archive   $LHAFILE_ARCHIVE $LHAFILE_URLBASE || exit 1
remove_builddir $LHAFILE_DIR
extract_archive $LHAFILE_ARCHIVE || exit 1
(
    cd_to_builddir $LHAFILE_DIR &&
    python2.7 setup.py install
) || exit 1

