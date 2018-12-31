#!/usr/bin/python
"""
pyreadline.py

TODO: Model this as a state machine?

Inputs:
  - entering a line that's incomplete
  - entering a line that finishes a command
  - hitting TAB for complete
  - Ctrl-C to cancel!  (make sure to delete stuff here)

Actions:
  - Display completions
  - Display a 1-line message showing lack of completions ('no variables that
    begin with $')
  - Execute a command
  - Clear N lines below the prompt (has to happen a lot)

"""
from __future__ import print_function

import readline
import signal
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def Words(prefix):
  #log('Words')
  words = ['foo', 'bar', 'baz', 'spam', 'eggs']
  first = 'echo '
  #first = 'echo\\ '  # Test quoting

  candidates = [first + w for w in words]

  for c in candidates:
    if c.startswith(prefix):
      yield c + ' '


class CompletionCallback(object):
  def __init__(self, comp_state):
    self.comp_state = comp_state
    self.iter = None

  def Call(self, word_prefix, state):
    """Generate completions."""

    #log('Called with %r %r', word_prefix, state)
    if state == 0:  # initial completion
      # Save for later
      self.comp_state['ORIG'] = readline.get_line_buffer()
      self.iter = Words(word_prefix)

    try:
      c = self.iter.next()
    except StopIteration:
      c = None
    return c

  def __call__(self, word_prefix, state):
    try:
      return self.Call(word_prefix, state)
    except Exception as e:
      # Readline swallows exceptions!
      print(e)
      raise


class DisplayCallback(object):
  """Hook to display completion candidates.

  This is useful for:
  - stripping off the common prefix according to OUR rules
  - display builtin and flag help

  Problem: how do I detect where the bottom of the screen is?

  Features here:
  - TODO: query terminal width
  - limit the number of matches to 10 or so?
    - so then do you need an option to set this limit?  COMPLIMIT?
    - what does readline do?
  """

  def __init__(self, comp_state, reader, max_lines=5):
    self.comp_state = comp_state
    self.reader = reader
    self.max_lines = max_lines  # TODO: Respect this!
    self.num_lines_last_displayed = 0

  def Reset(self):
    """Call this in between commands."""
    self.num_lines_last_displayed = 0

  def __call__(self, subst, matches, longest_match_len):
    if 0:
      log('')
      log('subst = %r', subst)
      log('matches = %s', matches)
      log('longest = %s', longest_match_len)
    print('')

    # Have to delete previous completions!
    EraseLines(self.num_lines_last_displayed)

    # Print and go back up.  But we have to ERASE these before hitting enter!
    for m in matches:
      print(m)
    n = len(matches)
    self.num_lines_last_displayed = n

    # Move up.  Hm this works.  But I need to erase the candidates after
    # hitting enter!
    sys.stdout.write('\x1b[%dA' % (n+1))  # UP

    # Also need to move back to the end of line, before readline?

    n = len(self.comp_state['ORIG']) + len(self.reader.prompt_str)
    sys.stdout.write('\x1b[%dC' % n)  # RIGHT


def EraseLines(n):
  if n == 0:
    return

  for i in xrange(n):
    sys.stdout.write('\x1b[0K')  # clear the line
    sys.stdout.write('\x1b[%dB' % 1)  # go down one line

  # Now go back up
  sys.stdout.write('\x1b[%dA' % (n))


def _SigIntHandler(unused, unused_frame):
  """Do nothing.

  Hm OSH doesn't do anything either.  I think we should cancel the command.

  I kind of like how fish deletes the prompt!  There is no evidence of the
  cancelled command.

  NOTE: What if were in a sleep state?  That seems to work.
  """
  pass


def RegisterSigIntHandler():
  signal.signal(signal.SIGINT, _SigIntHandler)


_PS1 = 'demo$ '
_PS2 = '> '  # A different length to test DisplayCallback


class InteractiveLineReader(object):
  """Simplified version of OSH prompt.

  Holds PS1 / PS2 state.
  """
  def __init__(self):
    self.prompt_str = ''
    self.pending_lines = []  # for completion to use
    self.Reset()  # initialize self.prompt_str

  def GetLine(self):
    try:
      line = raw_input(self.prompt_str) + '\n'  # newline required
    except EOFError:
      print('^D')  # bash prints 'exit'; mksh prints ^D.
      line = None
    else:
      self.pending_lines.append(line)

    self.prompt_str = _PS2  # TODO: Do we need $PS2?  Would be easy.
    return line

  def Reset(self):
    self.prompt_str = _PS1
    del self.pending_lines[:]


def MainLoop(reader, hook):
  while True:
    line = reader.GetLine()
    if line is None:
      break

    # Erase lines before execution or displaying PS2
    EraseLines(hook.num_lines_last_displayed)

    if line.endswith('\\\n'):
      continue

    # Write all the lines
    sys.stdout.write(''.join(reader.pending_lines))

    hook.Reset()
    reader.Reset()


def main(argv):
  RegisterSigIntHandler()

  # Right now this is used to set the original command.
  comp_state = {}

  readline.set_completer(CompletionCallback(comp_state))

  # If we do this, we get the whole line.  Then we need to use DisplayCallback
  # to get it.
  readline.set_completer_delims('')

  reader = InteractiveLineReader()
  hook = DisplayCallback(comp_state, reader)

  readline.set_completion_display_matches_hook(hook)

  readline.parse_and_bind('tab: complete')

  MainLoop(reader, hook)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
