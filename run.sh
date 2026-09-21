#!/bin/sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
STELLA_APP=${STELLA_APP:-}

if [ "$#" -ne 0 ]; then
  echo "Usage: sh ./run.sh (builds and runs Rescue Terri)" >&2
  exit 2
fi

if [ -z "$STELLA_APP" ]; then
  for candidate in \
    /Applications/Stella.app \
    "$HOME/Applications/Stella.app" \
    "$HOME"/.vscode/extensions/chunkypixel.atari-dev-studio-*/out/bin/emulators/stella/darwin/Stella.app; do
    if [ -x "$candidate/Contents/MacOS/Stella" ]; then
      STELLA_APP=$candidate
      break
    fi
  done
fi

if [ -z "$STELLA_APP" ] || [ ! -x "$STELLA_APP/Contents/MacOS/Stella" ]; then
  echo "### ERROR: Stella.app not found. Set STELLA_APP to its full app path." >&2
  exit 1
fi

# A failed build must not launch the previous ROM left in bin/.
sh "$SCRIPT_DIR/build.sh"
exec open -a "$STELLA_APP" "$SCRIPT_DIR/bin/rescue_terri.a26"
