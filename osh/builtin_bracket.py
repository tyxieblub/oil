#!/usr/bin/env python
"""
builtin_bracket.py
"""
from __future__ import print_function

from core import util
from core import meta
from core.meta import Id, IdInstance, runtime_asdl, syntax_asdl

from osh import expr_eval
from osh import bool_parse

word = syntax_asdl.word
bool_expr = syntax_asdl.bool_expr
value = runtime_asdl.value

log = util.log

_UNARY_LOOKUP = meta.TEST_UNARY_LOOKUP
_BINARY_LOOKUP = meta.TEST_BINARY_LOOKUP
_OTHER_LOOKUP = meta.TEST_OTHER_LOOKUP


class _StringWordEmitter(object):
  """For test/[, we need a word parser that returns StringWord.

  The BoolParser calls word.BoolId(w), and deals with Kind.BoolUnary,
  Kind.BoolBinary, etc.  This is instead of CompoundWord/TokenWord (as in the
  [[ case.
  """
  def __init__(self, argv):
    self.argv = argv
    self.i = 0
    self.n = len(argv)

  def ReadWord(self, unused_lex_mode):
    if self.i == self.n:
      # NOTE: Could define something special
      return word.StringWord(Id.Eof_Real, '')

    #log('ARGV %s i %d', self.argv, self.i)
    s = self.argv[self.i]
    self.i += 1

    # default is an operand word
    id_int = (
        _UNARY_LOOKUP.get(s) or _BINARY_LOOKUP.get(s) or _OTHER_LOOKUP.get(s))

    id_ = Id.Word_Compound if id_int is None else IdInstance(id_int)
    return word.StringWord(id_, s)


class _WordEvaluator(object):

  def EvalWordToString(self, w, do_fnmatch=False, do_ere=False):
    # do_fnmatch: for the [[ == ]] semantics which we don't have!
    # I think I need another type of node
    # Maybe it should be BuiltinEqual and BuiltinDEqual?  Parse it into a
    # different tree.
    return value.Str(w.s)


def _StringWordTest(s):
  # TODO: Could be Word_String
  return bool_expr.WordTest(word.StringWord(Id.Word_Compound, s))


def _TwoArgs(argv):
  """Returns an expression tree to be evaluated."""
  a0, a1 = argv
  if a0 == '!':
    return bool_expr.LogicalNot(_StringWordTest(a1))
  unary_id = _UNARY_LOOKUP.get(a0)
  if unary_id is None:
    # TODO:
    # - syntax error
    # - separate lookup by unary
    util.p_die('Expected unary operator, got %r (2 args)', a0)
  child = word.StringWord(Id.Word_Compound, a1)
  return bool_expr.BoolUnary(IdInstance(unary_id), child)


def _ThreeArgs(argv):
  """Returns an expression tree to be evaluated."""
  a0, a1, a2 = argv

  # NOTE: Order is important here.

  binary_id = _BINARY_LOOKUP.get(a1)
  if binary_id is not None:
    left = word.StringWord(Id.Word_Compound, a0)
    right = word.StringWord(Id.Word_Compound, a2)
    return bool_expr.BoolBinary(IdInstance(binary_id), left, right)

  if a1 == '-a':
    left = _StringWordTest(a0)
    right = _StringWordTest(a2)
    return bool_expr.LogicalAnd(left, right)

  if a1 == '-o':
    left = _StringWordTest(a0)
    right = _StringWordTest(a2)
    return bool_expr.LogicalOr(left, right)

  if a0 == '!':
    child = _TwoArgs(argv[1:])
    return bool_expr.LogicalNot(child)

  if a0 == '(' and a2 == ')':
    return _StringWordTest(a1)

  util.p_die('Syntax error: binary operator expected, got %r (3 args)', a1)


def Test(argv, need_right_bracket):
  """The test/[ builtin.

  The only difference between test and [ is that [ needs a matching ].
  """
  if need_right_bracket:
    if not argv or argv[-1] != ']':
      util.error('[: missing closing ]')
      return 2
    del argv[-1]

  w_parser = _StringWordEmitter(argv)
  b_parser = bool_parse.BoolParser(w_parser)

  # There is a fundamental ambiguity due to poor language design, in cases like:
  # [ -z ]
  # [ -z -a ]
  # [ -z -a ] ]
  #
  # See posixtest() in bash's test.c:
  # "This is an implementation of a Posix.2 proposal by David Korn."
  # It dispatches on expressions of length 0, 1, 2, 3, 4, and N args.  We do
  # the same here.
  #
  # Another ambiguity:
  # -a is both a unary prefix operator and an infix operator.  How to fix this
  # ambiguity?

  bool_node = None
  n = len(argv)
  try:
    if n == 0:
      return 1  # [ ] is False
    elif n == 1:
      bool_node = _StringWordTest(argv[0])
    elif n == 2:
      bool_node = _TwoArgs(argv)
    elif n == 3:
      bool_node = _ThreeArgs(argv)
    if n == 4:
      a0 = argv[0]
      if a0 == '!':
        child = _ThreeArgs(argv[1:])
        bool_node = bool_expr.LogicalNot(child)
      elif a0 == '(' and argv[3] == ')':
        bool_node = _TwoArgs(argv[1:3])
      else:
        pass  # fallthrough

    if bool_node is None:
      bool_node = b_parser.ParseForBuiltin()

  except util.ParseError as e:
    # TODO: There should be a nice method to print argv.  And some way to point
    # to the error.
    log("Error parsing %s", argv)
    util.error("test: %s", e.UserErrorString())
    return 2  # parse error is 2

  # mem: Don't need it for BASH_REMATCH?  Or I guess you could support it
  # exec_opts: don't need it, but might need it later

  mem = None  # Not necessary
  word_ev = _WordEvaluator()
  arena = None

  # We want [ a -eq a ] to always be an error, unlike [[ a -eq a ]].  This is a
  # weird case of [[ being less strict.
  class _DummyExecOpts():
    def __init__(self):
      self.strict_arith = True
  exec_opts = _DummyExecOpts()

  bool_ev = expr_eval.BoolEvaluator(mem, exec_opts, word_ev, arena)
  try:
    b = bool_ev.Eval(bool_node)
  except util.FatalRuntimeError as e:
    # e.g. [ -t xxx ]
    # TODO: Printing the location would be nice.
    util.error('test: %s', e.UserErrorString())
    return 2  # because this is more like a parser error.

  status = 0 if b else 1
  return status


if __name__ == '__main__':
  # Test
  e = _StringWordEmitter('-z X -o -z Y -a -z X'.split())
  while True:
    w = e.ReadWord(None)
    print(w)
    if w.id == Id.Eof_Real:
      break
