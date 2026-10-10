# Rescue Terri Notes

Reviewed against all six game sources and upstream batari Basic on **2026-10-10**.

## Build

- Project root: `/Users/luke/code/atari/batari/maze_game`
- Entry source: `rescue_terri.26b`; the game is split across the files listed below
- Standard compile command: `sh ./build.sh`
- Build and run in Stella on macOS: `sh ./run.sh`. It uses an installed Stella.app or Atari Dev Studio's bundled copy; `STELLA_APP` can override the app path.
- `build.sh` defaults `bB` to `/Users/luke/opt/batari-Basic` and runs `2600basic.sh`
- `build.sh` defaults to the full Rescue Terri build; an explicit `rescue_terri.26b` path does the same. Other standalone sources still compile individually.
- In VS Code, use **Terminal > Run Build Task** (`Cmd+Shift+B` on macOS) and the default **Build Rescue Terri** task. It builds the whole game regardless of the active editor file.
- To build and launch Stella, use **Terminal > Run Task > Build and Run Rescue Terri**. A failed build does not launch the previous ROM.
- Local VS Code user shortcuts map **F5** to save all files and run **Build and Run Rescue Terri**, and **Shift+F5** to save all files and run **Build Rescue Terri**. These bindings apply only to batari Basic files in this project's root and `src/` folder; other projects retain their existing shortcuts.
- Keyboard shortcuts live in the local VS Code user `keybindings.json`, not in this repository. A new checkout/machine has the tasks but needs its own shortcut bindings.
- Do not compile an individual fragment or the entry source directly with Atari Dev Studio's single-file build command. Use the task or `build.sh` so all fragments are included.
- `build.sh` combines the BASIC sources in the order below before invoking the compiler. The bB `include` command is for assembly modules, not these BASIC fragments.
- Compiler diagnostics of the form `N: message`, `line N: message`, or current `*** ERROR/WARNING  line N: message` are mapped back to the editable source file and local line number. Assembly-stage diagnostics still refer to generated assembly.
- Build-wrapper tests: `python3 -m unittest discover -s tests -v` (standard library only; uses a fake compiler, not Stella)
- Current CLI toolchain works in this repo with:
  - batari Basic `v1.9 (c)2025`
  - DASM `2.20.15-SNAPSHOT`

### Verified compiler revision

- [Latest published release: v1.9](https://github.com/batari-Basic/batari-Basic/releases/tag/v1.9), published 2025-10-13.
- [Latest upstream master: `efd6dcd319c31a5e37afb00d47c981105998d924`](https://github.com/batari-Basic/batari-Basic/commit/efd6dcd319c31a5e37afb00d47c981105998d924), dated 2026-01-08; checked against the remote on 2026-10-10. It includes changes after the v1.9 release while retaining the v1.9 version banner.
- `2600basic.sh` selects WebAssembly when Wasmtime is available. The five bB `.wasm` tools were rebuilt from that revision with WASI SDK 25 (the version in upstream CI). Native bB executables already matched a fresh build of the same source.
- The existing local launcher fallback patch is retained. The local native-launcher `dasm` wrapper uses `bB` to find `dasm.wasm`.
- Local binary hashes and the backup location are recorded in `/Users/luke/opt/batari-Basic/local-build-info.json`; original replaced files are backed up under `/Users/luke/opt/batari-Basic-backups/`.
- Do not use the version banner alone to verify freshness: the older release binary also reports v1.9 but rejects post-release `variable++` syntax.
- The game uses supported current commands: `const`, `dim`, `include`, `set romsize`, `if/then`, `goto`, `gosub`, `return thisbank`, `on ... goto`, `bank`, `playfield:`, `pfread`, `pfhline`, `sdata`/`sread`, `reboot`, and `drawscreen`. Arithmetic assignments and direct TIA register writes remain valid. Optional newer commands do not require a gameplay rewrite.
- Keep the explicit RAM map: `autodim` does not create extra memory. Keep BCD score arithmetic as `score = score + 1`, not `score++`.

## Source Navigation

### Temporary temple start for treasure-room development

- **Currently enabled:** `const TEST_START_IN_TEMPLE = 1` near the top of `rescue_terri.26b`.
- Starting from the title screen places both player-controlled missiles and Terri in `_room_bottom_left` (the temple), on open floor just above the ball: missile0 `(34,49)`, missile1 `(50,49)`, Terri `(41,49)`.
- Bring Terri to the exact ball capture anchor `(39,54)` (two pixels left and five down from the test spawn), then use fire to resume after discovery. The normal passage to `_room_hidden` opens on the left. The ball/discovery sequence remains active; the house stays in `ROOM_RIGHT`.
- **Restore the full game:** change only `TEST_START_IN_TEMPLE` to `0`, then run `sh ./build.sh` or `sh ./run.sh`. This restores the original room, missile positions, and Terri position. Reset returns to the title and uses the selected start mode again.
- `_start_game` in `src/screens.26b` enters `_start_game_room` in bank 2. The assembler conditional there selects the test setup or the original `_inititial_game_room`; it adds no RAM state or bank 1 test logic.

These files share one global variable and label namespace. Explicit `bank` declarations in `src/rooms.26b` and `src/music.26b` select banks 2 and 3; the build order must keep those declarations after all bank 1 code.

| Compilation order | File | Contents | ROM bank |
|---|---|---|---|
| 1 | [rescue_terri.26b](rescue_terri.26b) | Constants, RAM aliases, sprite setup, startup | 1 |
| 2 | [src/gameplay.26b](src/gameplay.26b) | Main loop, joystick/wall checks, Terri AI, score, ball blink and discovery | 1 |
| 3 | [src/screens.26b](src/screens.26b) | Title screen, celebration flow, fire-button handling, starting a game | 1 |
| 4 | [src/room_exits.26b](src/room_exits.26b) | Room boundary checks and transition dispatch | 1 |
| 5 | [src/rooms.26b](src/rooms.26b) | Bank 2 declaration, room loaders/playfields, doorway placement, colors, hidden passage | 2 |
| 6 | [src/music.26b](src/music.26b) | Bank 3 declaration, two-channel playback and all song data | 3 |

- To change a song, look for its `sdata` block in `src/music.26b`. Bass and melodies all use four-byte events: volume, control, frequency, and duration in frames. Match the existing two-line layout (`8,12,26` then `28`); rests use `0,0,0` then their duration. A single `255` ends each stream. Keep the bass chord comments above their sections.
- To edit the Temple Room, find `_room_bottom_left` in `src/rooms.26b`; the Treasure Room is `_room_hidden` in the same file.
- Keep playfields with their room loader. `maze.txt` is a reference, not compiler input.
- To add/reorder a fragment, update the explicit list in `build.sh`. Never compile a glob of `src/*.26b`; alphabetical order is not execution order.
- Music playback and all streams now occupy bank 3. Adding treasure-room music remains a separate future change.

## Build Outputs

- Standard build output location is `bin/`:
  - `bin/rescue_terri.26b.asm`
  - `bin/rescue_terri.26b.bin`
  - `bin/rescue_terri.26b.lst`
  - `bin/rescue_terri.26b.sym`
  - `bin/rescue_terri.a26`
- `build.sh` names outputs from the source basename, so alternate sources still emit `bin/<source>.{asm,bin,lst,sym}` and `bin/<stem>.a26`
- Compiler intermediates are moved into `.cache/`:
  - `.cache/bB.asm`
  - `.cache/2600basic_variable_redefs.h`
  - `.cache/includes.bB`
- Generated build input and diagnostics (ignored by Git):
  - `.cache/combined/rescue_terri.26b` - combined source; do not edit
  - `.cache/combined/source-map.tsv` - combined starting line and source path for each nonempty fragment
  - `.cache/build.log` - unmodified compiler output from the latest build
- A failed build preserves the last successful `.bin` and `.a26`; check build status before running a ROM. Generated assembly/listings may reflect the failed attempt.
- Obsolete April music-probe source and outputs were moved from `.cache/` to `poc/cache-archive-2026-10-10/`; they are historical experiments, not current game inputs.
- Refresh generated cache files by running `sh ./build.sh`. Refresh the command reference separately against upstream compiler source and the linked manual; it is tracked documentation, not generated output. `.cache/build.log` describes only the latest build, including standalone builds.
- Verified `rescue_terri.26b` build budget (2026-10-10):
  - `574 bytes of ROM space left in bank 1`
  - `1124 bytes of ROM space left in bank 2` (temple test start enabled; 1156 with it disabled)
  - `3304 bytes of ROM space left in bank 3`
  - `2702 bytes of ROM space left in bank 4`

## Local References

- Use `.cache/bb_commands_reference.md` as the local batari Basic reference
- `include div_mul.asm` is already used by the project (provides multiplication/division)
- `maze.txt` starts with the original 96×33, nine-room layout reference. Appended layouts describe the unlocked temple and the tenth, hidden room outside that grid.
- `maze.txt` legend markers (`A`, `B`, `C`, `D`, `<>`) are annotations only; they are not present in the compiled playfield data

## Variable Register Map

All 26 registers (a–z) are assigned. Do not use a register without first checking this map:

| Register | Alias | Purpose |
|---|---|---|
| a | j0_debounce_up_down | joystick 0 up/down debounce counter |
| b | j0_debounce_left_right | joystick 0 left/right debounce counter |
| c | j1_debounce_up_down | joystick 1 up/down debounce counter |
| d | j1_debounce_left_right | joystick 1 left/right debounce counter |
| e | mi_room_number | room both missiles are currently in |
| f | p1_room_number | room player1 is currently in |
| g | p1_y | saved y position of player1 when hidden |
| h | p1_dx | player1 x movement direction (-1, 0, 1) |
| i | p1_dy | player1 y movement direction (-1, 0, 1) |
| j | p1_move_counter | frames elapsed since last player1 move |
| k | p0_room_number | room player0 (objective) is currently in |
| l | game_over | 0 = playing, non-zero = game over |
| m | color_cycle | current color index during game over (0–8) |
| n | color_cycle_timer | frames elapsed in current color step |
| o | p0_y | saved y position of player0 when hidden |
| p | game_state | STATE_TITLE=0 or STATE_PLAY=1 |
| q | title_bass_duration | title music bass duration counter |
| r | title_melody_duration | title music melody duration counter |
| s | title_music_setup_mode | title music setup return mode |
| t | title_melody_phrase | current title melody phrase index (0–15) |
| u/v | _Title_Bass sdata pointer | title music bass stream pointer |
| w/x | shared melody sdata pointer | `_Title_Melody`, `_Title_Melody_2`, `_Title_Melody_3`, `_Easter_Egg_Melody`, or `_Victory_Melody` |
| y | score_frame_counter | frames elapsed since the last score increment |
| z | easter_egg_found | non-zero after the temple easter egg is found; selects the alternate game-over melody |

Temp variables `temp1`–`temp6` are used within single logical blocks and clobbered by `drawscreen` (not guaranteed to become zero). They are re-aliased at point of use (e.g. `dim mid_delta = temp3`). Playfield/library commands can also use scratch RAM; check their implementation before keeping temps live across a call.

## Key Constants

```
; Screen boundaries (missile movement limits)
SCR_LEFT_X  = 18     SCR_RIGHT_X = 142
SCR_TOP_Y   = 4      SCR_BOT_Y   = 87
OFFSCRN_Y   = 200    ; y value used to hide sprites off-screen
SCORE_COLOR = $2E    ; gold score color

; Entry gate positions (where missiles/player1 appear when entering a room)
ENTRY_GATE_LEFT_X  = 22    ENTRY_GATE_RIGHT_X = 138
ENTRY_GATE_TOP_Y   = 8     ENTRY_GATE_BOT_Y   = 79

; Temple easter egg ball
TEMPLE_BALL_X = 41    TEMPLE_BALL_Y = 53
TEMPLE_BALL_CAPTURE_X = 39    TEMPLE_BALL_CAPTURE_Y = 54
TEMPLE_BALL_VISIBLE_FRAMES = 45 ; visible frames per 60-frame score timer cycle

; Missile dimensions
MISSLE_WIDTH  = 4    MISSLE_HEIGHT = 4
MISSLE_WIDTH_BIN = %00100000   ; value for NUSIZ0/NUSIZ1

; Playfield coordinate system offsets (used in pfread collision math)
PF_SCR_X_OFFSET = 18    PF_SCR_Y_OFFSET = 3

; Player1 behavior
P1_MOVE_DELAY      = 3   ; skip 3 frames; step on the 4th eligible frame
P1_GATE_THRESHOLD  = 2   ; how close player1 must be to a doorway to transfer rooms
COLOR_CYCLE_DELAY  = 12  ; advance color on the 13th loop iteration
SCORE_FRAMES_PER_SECOND = 60 ; frames per score increment

; Win target inside the house (different from the house sprite origin)
HOUSE_ENTRY_X = 129    HOUSE_ENTRY_Y = 74

; Input debounce
J_DEBOUNCE_DELAY = 4
```

## Game Structure

- `missile0` and `missile1` are the two player-controlled objects (joystick 0 and 1)
- `player1` is an AI sprite that moves toward the midpoint of missile0 and missile1
- `player0` is the stationary objective sprite
- `ball` is only used for the temple easter egg in `ROOM_BOTTOM_LEFT`
- Victory starts when `player1` reaches `(HOUSE_ENTRY_X, HOUSE_ENTRY_Y) = (129, 74)` in `player0`'s room. The house sprite itself starts at `(127, 75)`.
- Centering the temple ball inside Terri's hollow square triggers the easter egg: `player1x = TEMPLE_BALL_CAPTURE_X` and `player1y = TEMPLE_BALL_CAPTURE_Y`, exactly `(39,54)`, in `ROOM_BOTTOM_LEFT`. Edge contact does not collect it. This swaps the `player1` sprite art and uses `_Easter_Egg_Melody` instead of `_Victory_Melody`.
- Discovery also clears playfield columns 0–1 in rows 7–8 of `ROOM_BOTTOM_LEFT`, revealing the passage to `ROOM_HIDDEN`. The opening is visible during the celebration.
- Either fire button resumes play after the easter egg, silences the music, and restores room colors. The passage stays open on subsequent visits until Reset starts a new run.
- Game over freezes play and cycles the room colors through 9 presets
- Title screen is active until either fire button is pressed
- Title screen plays two-voice music:
  - `_Title_Bass` on channel 1 (`AUDV1`/`AUDC1`/`AUDF1`)
  - `_Title_Melody` on channel 0 (`AUDV0`/`AUDC0`/`AUDF0`)
  - `_Title_Melody_2` is the second melody section, also on channel 0
  - `_Title_Melody_3` is the third melody section, also on channel 0
  - Bass phrase is 512 frames; its 16 notes retain 28 sounding frames plus a 4-frame rest each, with timing now specified in the data rather than hard-coded in playback
  - Melody sections 1 and 2 are 128 frames each; section 3 is 256 frames
  - Phrase indices 0–3 play section 1, 4–7 play section 2, 8–11 repeat section 1, and 12–15 play section 3, then wrap to 0 (2560 frames total)
  - The title playfield changes to white, gold, or teal with melody section 1, 2, or 3 respectively

## Collision Detection — Two Separate Systems

**1. Missile-wall collision (manual, using `pfread`):**
Wall collision is NOT done with the hardware `collision()` function. Instead, the code manually calculates the missile's playfield grid coordinates and calls `pfread(x, y)` to check if a wall pixel is set before allowing movement. This happens every frame in the joystick input section (bank 1).

The coordinate math:
- Playfield x column: `(screen_x - PF_SCR_X_OFFSET) / 4`
- Playfield y row:    `(screen_y - PF_SCR_Y_OFFSET) / 8`
- Both leading and trailing edges of each missile are checked before a move is allowed.

**2. Player1/Player0 game-over collision (position comparison, not hardware):**
```
if p0_room_number = p1_room_number && player1x = HOUSE_ENTRY_X && player1y = HOUSE_ENTRY_Y then goto _start_game_over
```
This is a direct variable comparison, not a hardware collision register check.

The hardware `collision()` function is not currently used anywhere in the game.

## Sprite Hiding

When a sprite is not in the current room (`mi_room_number`), it is hidden by setting its `y` to `OFFSCRN_Y = 200`. The real y is saved first:
- `p1_y` saves/restores `player1y`
- `p0_y` saves/restores `player0y`

This is checked each frame in the p0/p1 logic section.

The temple ball is separate from the sprite hide/show system:
- `ballx` is fixed at `TEMPLE_BALL_X`
- Before discovery in `ROOM_BOTTOM_LEFT`, `bally` is `TEMPLE_BALL_Y` for score timer frames 0-44 and `OFFSCRN_Y` for frames 45-59 (about 0.75 seconds on, 0.25 seconds off at 60 Hz)
- The blink reuses `score_frame_counter`, adds no RAM variable, and leaves collection active at the fixed temple coordinates even while hidden
- In other rooms, `bally` is always `OFFSCRN_Y`
- finding the easter egg immediately hides the ball for the rest of that run

## Playfield Drawing — Runtime `playfield:` Updates

Base room walls are stored as `playfield:` blocks inside the bank 2 room init routines. `_open_hidden_passage` uses two `pfhline ... off` operations to clear the temple doorway, both on discovery and after reloading the temple when `easter_egg_found` is set.

Why this still works with collision:
1. Each room transition jumps into bank 2 and rewrites the active playfield RAM for the destination room
2. `pfread()` always checks that current playfield RAM, so collision stays aligned with the visible room
3. The title screen also uses a `playfield:` block, but only for the title layout

Use the source playfields as authoritative: the main `maze.txt` grid still contains older right-room geometry. Its appended layouts document the unlocked temple and hidden room.

## Bank Switching Structure

- `set romsize 16k` - 4 banks of 4K each
- **Bank 1:** everything that runs every frame (input, AI, p0/p1 logic, game-over, title loop, boundary-check dispatch stubs)
- **Bank 2:** room setup, temple/hidden-room exit selection, passage reveal, and celebration/resume color helpers
- **Bank 3:** two-channel music playback, stream setup, and bass/title/victory/easter-egg data
- **Bank 4:** compiler-provided kernel and sprite graphics
- `_start_game_room` selects the new-game start using `TEST_START_IN_TEMPLE`; `_inititial_game_room` is the original `ROOM_RIGHT` playfield/data entry used when the test start is disabled

Each bank 2 room routine ends with `goto _end_boundary_check bank1` to return to the main loop.

**Cost:** `goto bankN` = 49 cycles per jump. A room transition jumps to bank 2 and back; celebration colors also use bank 2. Keep cross-bank jumps to a minimum.

**Important:** Data tables can only be accessed from within the same bank they are defined in.
Music readers and all `sdata` streams therefore live together in bank 3. Bank 1 enters music with `goto ... bank3`; music returns to title/celebration flow with `goto ... bank1`. Bank 2 celebration colors enter `_title_music_loop bank3`. Keep these cross-bank destinations explicit.

## Room Logic

- Room transitions are decided in the bank 1 boundary-check section
- `ROOM_BOTTOM_LEFT` and `ROOM_HIDDEN` share horizontal edge checks. Bank 2 routes their exits; entry to the hidden room requires `easter_egg_found`.
- Missile repositioning for the new room happens inside the bank 2 room init label
- Player1 doorway-follow logic also lives inside the destination room init block
- Player1 is pulled through a doorway only if it is in the room being left, visible, and within `P1_GATE_THRESHOLD`
- Horizontal transfers preserve `player1y`; vertical transfers preserve `player1x`

## Current Room Map

```
ROOM_RIGHT       = 1
ROOM_MIDDLE      = 2
ROOM_LEFT        = 3
ROOM_TOP         = 4
ROOM_BOTTOM      = 5
ROOM_TOP_RIGHT   = 6
ROOM_TOP_LEFT    = 7
ROOM_BOTTOM_LEFT = 8
ROOM_BOTTOM_RIGHT= 9
ROOM_HIDDEN      = 10
```

Connections (implemented):
```
ROOM_RIGHT <-> ROOM_MIDDLE  (left/right doorway)
ROOM_MIDDLE <-> ROOM_LEFT   (left/right doorway)
ROOM_MIDDLE <-> ROOM_TOP    (top/bottom doorway)
ROOM_MIDDLE <-> ROOM_BOTTOM (top/bottom doorway)
ROOM_TOP    <-> ROOM_TOP_RIGHT
ROOM_TOP    <-> ROOM_TOP_LEFT
ROOM_LEFT   <-> ROOM_TOP_LEFT
ROOM_BOTTOM <-> ROOM_BOTTOM_LEFT
ROOM_BOTTOM <-> ROOM_BOTTOM_RIGHT
ROOM_RIGHT  <-> ROOM_BOTTOM_RIGHT
ROOM_BOTTOM_LEFT <-> ROOM_HIDDEN (left/right doorway; unlocked by the easter egg)
```

`maze.txt` slice layout:
```
ROOM_TOP_LEFT     ROOM_TOP     ROOM_TOP_RIGHT
ROOM_LEFT         ROOM_MIDDLE  ROOM_RIGHT
ROOM_BOTTOM_LEFT  ROOM_BOTTOM  ROOM_BOTTOM_RIGHT
```

Room colors:
```
ROOM_RIGHT        BLACK / WHITE
ROOM_MIDDLE       ORANGE_DARK / ORANGE_LIGHT
ROOM_LEFT         GRAY_DARK / GRAY_LIGHT
ROOM_TOP          GREEN_DARK / GREEN_LIGHT
ROOM_BOTTOM       PURPLE_DARK / PURPLE_LIGHT
ROOM_TOP_RIGHT    GOLD_DARK / GOLD_LIGHT
ROOM_TOP_LEFT     BRICK_DARK / BRICK_LIGHT
ROOM_BOTTOM_LEFT  OLIVE_DARK / OLIVE_LIGHT
ROOM_BOTTOM_RIGHT TEAL_DARK / TEAL_LIGHT
ROOM_HIDDEN       BLACK / GOLD_LIGHT
```

## Editing Guidance

- **ROM space is tight.** Prefer small, targeted changes. Check `.cache/bB.asm` and `.lst` after building to monitor bank usage.
- Music code and tables share bank 3, with 3304 bytes currently free. Add streams there alongside their readers; bank 2's free space is not directly available to bank 3 `sread()` calls.
- When adding a room: update bank 1 boundary routing AND add the room init block in bank 2
- When adding a room connection: update the boundary check for both rooms involved
- When changing room geometry: keep `maze.txt` and the matching 32×11 `playfield:` block in sync
- Keep sprite colors readable against each room's background/playfield colors
- There are currently no free registers; all new variable aliases must reuse an existing register only when the usage does not overlap
- Do not reuse `u`/`v` or `w`/`x` for frame-to-frame state while title music is active; they are `sdata` pointers
- Temp variables (`temp1`–`temp6`) are safe to re-alias within a block but are clobbered by `drawscreen` — never rely on them across frames
- Do not use `collision()` for wall detection — the manual `pfread()` system is intentional and required for the coordinate-based approach
