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
  SOURCE_FILE=rescue_terri.26b
fi

SOURCE_BASENAME=$(basename "$SOURCE_FILE")
SOURCE_STEM=${SOURCE_BASENAME%.*}

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

if [ ! -f "$SOURCE_FILE" ]; then
  echo "### ERROR: Source file not found: $SOURCE_FILE" >&2
  exit 1
fi

SOURCE_DIR=$(CDPATH= cd -- "$(dirname "$SOURCE_FILE")" && pwd)
COMPILE_SOURCE="$SOURCE_DIR/$SOURCE_BASENAME"
SOURCE_MAP=""
BUILD_LOG="$CACHE_DIR/build.log"

combine_sources() {
  for source do
    if [ ! -f "$source" ]; then
      echo "### ERROR: Missing source fragment: $source" >&2
      return 1
    fi
  done

  # Retain source order and record original file boundaries for diagnostics.
  awk -v map="$SOURCE_MAP" '
    FNR == 1 { printf "%d\t%s\n", NR, FILENAME > map }
    { print }
  ' "$@" > "$COMPILE_SOURCE"
}

if [ "$COMPILE_SOURCE" = "$SCRIPT_DIR/rescue_terri.26b" ]; then
  mkdir -p "$CACHE_DIR/combined"
  COMPILE_SOURCE="$CACHE_DIR/combined/rescue_terri.26b"
  SOURCE_MAP="$CACHE_DIR/combined/source-map.tsv"
  combine_sources \
    "$SCRIPT_DIR/rescue_terri.26b" \
    "$SCRIPT_DIR/src/gameplay.26b" \
    "$SCRIPT_DIR/src/screens.26b" \
    "$SCRIPT_DIR/src/music.26b" \
    "$SCRIPT_DIR/src/room_exits.26b" \
    "$SCRIPT_DIR/src/rooms.26b"
elif [ "$SOURCE_DIR" = "$SCRIPT_DIR/src" ]; then
  echo "### ERROR: Build the whole game with sh ./build.sh, not a source fragment." >&2
  exit 1
fi

# Require fresh compiler output; retain the last successful ROM on failure.
rm -f "$COMPILE_SOURCE.asm" "$COMPILE_SOURCE.bin" "$COMPILE_SOURCE.lst" "$COMPILE_SOURCE.sym"
# The WebAssembly toolchain exposes the project directory using relative paths.
COMPILE_ARGUMENT=${COMPILE_SOURCE#"$SCRIPT_DIR/"}
if bB="$BB_HOME" "$BB_HOME/2600basic.sh" "$COMPILE_ARGUMENT" "$@" > "$BUILD_LOG" 2>&1; then
  build_status=0
else
  build_status=$?
fi

if [ -n "$SOURCE_MAP" ]; then
  awk -F '\t' '
    NR == FNR { starts[++count] = $1 + 0; files[count] = $2; next }
    /^(line +)?[0-9]+:/ {
      line = $0
      sub(/^line +/, "", line)
      sub(/:.*/, "", line)
      line += 0
      for (i = count; i > 1 && starts[i] > line; i--) {}
      message = $0
      sub(/^(line +)?[0-9]+: */, "", message)
      printf "%s:%d: %s\n", files[i], line - starts[i] + 1, message
      next
    }
    { print }
  ' "$SOURCE_MAP" "$BUILD_LOG"
else
  cat "$BUILD_LOG"
fi

if [ "$build_status" -eq 0 ] && [ ! -f "$COMPILE_SOURCE.bin" ]; then
  echo "### ERROR: Compiler did not produce a ROM; see $BUILD_LOG" >&2
  build_status=1
elif [ "$build_status" -eq 0 ]; then
  # The bundled launcher can exit zero even when DASM emits a partial ROM.
  if ! awk '/^Complete[.] [(]0[)][[:space:]]*$/ { complete = 1 } END { exit !complete }' "$BUILD_LOG"; then
    echo "### ERROR: DASM did not report successful assembly; see $BUILD_LOG" >&2
    build_status=1
  fi
fi

move_if_exists "$SCRIPT_DIR/bB.asm" "$CACHE_DIR/bB.asm"
move_if_exists "$SCRIPT_DIR/2600basic_variable_redefs.h" "$CACHE_DIR/2600basic_variable_redefs.h"
move_if_exists "$SCRIPT_DIR/includes.bB" "$CACHE_DIR/includes.bB"

for ext in asm lst sym; do
  move_if_exists "$COMPILE_SOURCE.$ext" "$BIN_DIR/$SOURCE_BASENAME.$ext"
done

if [ "$build_status" -eq 0 ]; then
  move_if_exists "$COMPILE_SOURCE.bin" "$BIN_DIR/$SOURCE_BASENAME.bin"
  cp -f "$BIN_DIR/$SOURCE_BASENAME.bin" "$BIN_DIR/$SOURCE_STEM.a26"
fi

exit "$build_status"
