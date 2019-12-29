
import sys

if sys.maxsize == 0x7fffffff:
    logname = "dailybuild.log"
elif sys.maxsize == 0x7fffffffffffffff:
    logname = "dailybuild_x64.log"
else:
    assert False

with open(logname, "r+") as f:
    a, b = str(f.read()).splitlines()
    b = chr(ord(b)-1)
    f.seek(0)
    f.write("\n".join((a, b)))
