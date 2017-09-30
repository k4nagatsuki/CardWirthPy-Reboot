#! /bin/sh
cd $(dirname "$0")
cp Data/Font/*.ttf /Library/Fonts
/opt/X11/bin/fc-cache -frv

