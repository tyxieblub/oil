#!/usr/bin/python
"""
demo2.py
"""
from __future__ import print_function

import sys

from _devbuild.gen import demo2_typed_asdl as demo_asdl

op_id_e = demo_asdl.op_id_e

cflow = demo_asdl.cflow
cflow_e = demo_asdl.cflow_e

source_location = demo_asdl.source_location


def main(argv):
  print('Hello from demo2.py')

  op = op_id_e.Plus

  n1 = cflow.Break()
  n2 = cflow.Return()  # hm I would like a type error here

  n3 = cflow.Return('hi')

  print(n1)
  print(n2)
  print(n3)

  for n in [n1, n2, n3]:
    print(n.tag)

  loc = source_location('foo', 13, 0, 2)
  print(loc)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
