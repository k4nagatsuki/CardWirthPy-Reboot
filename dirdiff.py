#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil


def create_dirdiff(dpath1, dpath2, target):
    """
    ディレクトリdpath1に対するdpath2の差分を
    ディレクトリtargetに生成する。
    """
    for fpath in os.listdir(dpath1):

        fpath1 = os.path.join(dpath1, fpath)
        fpath2 = os.path.join(dpath2, fpath)
        target2 = os.path.join(target, fpath)

        if not os.path.exists(fpath2):

            print("Not found: %s" % (fpath1))
            if not os.path.isdir(os.path.dirname(target2)):
                os.makedirs(os.path.dirname(target2))
            if os.path.isdir(fpath1):
                shutil.copytree(fpath1, target2)
            else:
                shutil.copy2(fpath1, target2)

        elif os.path.isdir(fpath1):

            create_dirdiff(fpath1, fpath2, target2)

        else:
            with open(fpath1, "rb") as f1:
                with open(fpath2, "rb") as f2:
                    if f1.read() != f2.read():
                        print("Modified : %s" % (fpath1))
                        if not os.path.isdir(os.path.dirname(target2)):
                            os.makedirs(os.path.dirname(target2))
                        shutil.copy2(fpath1, target2)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python dirdiff.py <new> <old> [<target>]")
        sys.exit(0)

    dpath1 = sys.argv[1]
    dpath2 = sys.argv[2]

    print("Create DirDiff:")
    print(" New: %s" % (dpath1))
    print(" Old: %s" % (dpath2))
    if len(sys.argv) < 4:
        target = "dirdiffed"
    else:
        target = sys.argv[3]

    create_dirdiff(dpath1, dpath2, target)
