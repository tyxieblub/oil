#!/usr/bin/env bash

PS1='\h '
test "${PS1@P}" = "$(hostname -s) "  # short name
echo status=$?
PS1='\H '
test "${PS1@P}" = "$(hostname) "
echo status=$?
# unsure why this is needed, but if not set, osh will output like 5 "status=0"
exit 0
