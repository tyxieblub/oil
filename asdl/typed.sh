#!/bin/bash
#
# Usage:
#   ./typed.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

main() {
  echo 'Hello from typed.sh'
}

mypy() { ~/.local/bin/mypy "$@"; }

typecheck() {
  #mypy --py2 --strict "$@"
  mypy --py2 "$@"
}

check-arith() {
  PYTHONPATH=. typecheck asdl/arith_parse_typed.py #asdl/tdop.py
}

iter() {
  asdl/run.sh gen-demo-typed-asdl
  check-arith
}

iter2() {
  asdl/run.sh gen-demo2-asdl
  typecheck _devbuild/gen/demo2_typed_asdl.py asdl/demo2.py

  asdl/demo2.py "$@"
}

"$@"
