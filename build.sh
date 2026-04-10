#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
BB_HOME=${bB:-/Users/luke/opt/batari-Basic}
BIN_DIR="$SCRIPT_DIR/bin"
CACHE_DIR="$SCRIPT_DIR/.cache"

if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
  SOURCE_FILE=$1
  shift
else
  SOURCE_FILE=maze_game.26b
fi

SOURCE_BASENAME=$(basename "$SOURCE_FILE")

if [ ! -x "$BB_HOME/2600basic.sh" ]; then
  echo "### ERROR: couldn't find 2600basic.sh at $BB_HOME"
  echo "Set bB to your batari Basic install path and try again."
  exit 1
fi

move_if_exists() {
  src=$1
  dest=$2

  if [ -f "$src" ]; then
    mv -f "$src" "$dest"
  fi
}

mkdir -p "$BIN_DIR" "$CACHE_DIR"

cd "$SCRIPT_DIR"

set +e
bB="$BB_HOME" "$BB_HOME/2600basic.sh" "$SOURCE_FILE" "$@"
build_status=$?
set -e

move_if_exists "$SCRIPT_DIR/bB.asm" "$CACHE_DIR/bB.asm"
move_if_exists "$SCRIPT_DIR/2600basic_variable_redefs.h" "$CACHE_DIR/2600basic_variable_redefs.h"
move_if_exists "$SCRIPT_DIR/includes.bB" "$CACHE_DIR/includes.bB"

for ext in asm bin lst sym; do
  move_if_exists "$SCRIPT_DIR/$SOURCE_FILE.$ext" "$BIN_DIR/$SOURCE_BASENAME.$ext"
done

exit "$build_status"
