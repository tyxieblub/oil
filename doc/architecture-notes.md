Notes on OSH Architecture
=========================

# Parser Issues

## Where we (unfortunately) must re-parse previously parsed text

These cases make it harder to produce good error messages with source location
info.  They also have implications for translation, because we break the "arena
invariant".

(1) **`alias` expansion**.  Aliases are like "lexical macros".

(2) **Array L-values** like `a[x+1]=foo`.

NOTE: bash supports this across word boundaries: `a[x + 1]=foo`.  But this
causes problems for the parser, and I don't see it used.

Where bash re-parses strings at runtime:

(3) The **`unset` builtin** (not yet implemented in OSH):

    $ a=(1 2 3 4)
    $ expr='a[1+1]'
    $ unset "$expr"
    $ argv "${a[@]}"
    ['1', '2', '4']

(4) **Var refs** with `${!x}` (relied on by `bash-completion`, as discovered by
Greg Price)

    $ a=(1 2 3 4)
    $ expr='a[1+1]'
    $ echo "$expr"
    3

## Where VirtualLineReader is used

This isn't necessarily re-parsing, but it's re-reading.

- alias expansion:
- HereDoc:  We first read lines, and then

### Extra Passes Over the LST

These are handled up front, but not in a single pass.

- Assignment / Env detection: `FOO=bar declare a[x]=1`
  - s=1 doesn't cause reparsing, but a[x+1]=y does.
- Brace Detection in a few places: `echo {a,b}`
- Tilde Detection: `echo ~bob`, `home=~bob`

## Parser Lookahead

- `func() { echo hi; }` vs.  `func=()  # an array`
- precedence parsing?  I think this is also a single token.

## Where the arena invariant is broken

- Here docs with <<-.  The leading tab is lost, because we don't need it for
  translation.

## Where parsers are instantiated

- See `osh/parse_lib.py` and its callers.

# Runtime Issues

## Where code strings are evaluated

- source and eval
- trap
  - exit
  - debug
  - err
  - signals
- PS1 and PS4 (WordParser is used)

### Function Callbacks

- completion hooks registered by `complete -F ls_complete_func ls`
- bash has a `command_not_found` hook; osh doesn't yet

## Parse errors at runtime (need line numbers)

- [ -a -a -a ]
- command line flag usage errors

## Where unicode is respected

- ${#s} -- length in code points
- ${s:1:2} -- offsets in code points
- ${x#?} and family (not yet implemented)

Where bash respects it:

- [[ a < b ]] and [ a '<' b ] for sorting
- ${foo,} and ${foo^} for lowercase / uppercase

## Parse-time and Runtime Pairs

- echo -e '\x00\n' and echo $'\x00\n' (shared in OSH)
- test / [ and [[ (shared in OSH)

### Other Pairs

- expr and $(( )) (expr not in shell)
- later: find and our own language

# Build Time

## Dependencies

- Optional: readline

## Borrowed Code

- All of OPy:
  - pgen2
  - compiler2 from stdlib
  - byterun
- ASDL front end from CPython (heavily refactored)
- core/tdop.py: Heavily adapted from tinypy

## Generated Code

- See `build/dev.sh`

