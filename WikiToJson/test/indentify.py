#!/usr/bin/env python3

import sys

fl = sys.argv[1]
out = open(fl + "_out", "w+")
indent = 0;
increment = 2;
input = open(fl, "r").read()
for c in input:
    if c == '[':
        indent += increment
        out.write('[\n' + ' ' * indent)
    elif c == ']':
        indent -= increment
        out.write(']\n' + ' ' * indent)
    else:
        out.write(c)

out.close();
