#!/usr/bin/sh
set -x
cd $1
datestring=$(date +%Y%m%d%H%M%S)
echo movies_$datestring
mkdir movies_$datestring
mv *.mpg movies_$datestring/
mv *.wmv movies_$datestring/
cd movies_$datestring
for file in $(ls)
do
    ffmpeg -i $file -vcodec mpeg1video -acodec libmp3lame -intra ../$file
done

