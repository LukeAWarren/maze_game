# Rescue Terri Notes

## Build

- Project root: `/Users/luke/code/atari/batari/maze_game`
- Main source: `rescue_terri.26b`
- Standard compile command: `sh ./build.sh`
- `build.sh` defaults `bB` to `/Users/luke/opt/batari-Basic` and runs `2600basic.sh`
- `build.sh` now defaults to `rescue_terri.26b`; passing an explicit source still works
- Current CLI toolchain works in this repo with:
  - batari Basic `v1.9 (c)2025`
  - DASM `2.20.15-SNAPSHOT`

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
- If ADS is used directly, it may also refresh files under `bin/`
- Latest known `rescue_terri.26b` build budget:
  - `40 bytes of ROM space left in bank 1`
  - `437 bytes of ROM space left in bank 2`

## Local References

- Use `.cache/bb_commands_reference.md` as the local batari Basic reference
- `include div_mul.asm` is already used by the project (provides multiplication/division)
- `maze.txt` is the full 96×33 room layout reference; each `rescue_terri.26b` room playfield is a 32×11 slice from it
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
| t | title_melody_phrase | current title melody phrase index (0–7) |
| u/v | _Title_Bass sdata pointer | title music bass stream pointer |
| w/x | _Title_Melody/_Title_Melody_2 sdata pointer | title music melody stream pointer |
| y | score_frame_counter | frames elapsed since the last score increment |
| z | easter_egg_found | non-zero after the temple easter egg is found; selects the alternate game-over melody |

Temp variables `temp1`–`temp6` are used within single logical blocks and reset after `drawscreen`. They are re-aliased at point of use (e.g. `dim mid_delta = temp3`).

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

; Missile dimensions
MISSLE_WIDTH  = 4    MISSLE_HEIGHT = 4
MISSLE_WIDTH_BIN = %00100000   ; value for NUSIZ0/NUSIZ1

; Playfield coordinate system offsets (used in pfread collision math)
PF_SCR_X_OFFSET = 18    PF_SCR_Y_OFFSET = 3

; Player1 behavior
P1_MOVE_DELAY      = 3   ; frames between player1 steps toward midpoint
P1_GATE_THRESHOLD  = 2   ; how close player1 must be to a doorway to transfer rooms
COLOR_CYCLE_DELAY  = 12  ; frames per color step during game over
SCORE_FRAMES_PER_SECOND = 60 ; frames per score increment

; Input debounce
J_DEBOUNCE_DELAY = 4
```

## Game Structure

- `missile0` and `missile1` are the two player-controlled objects (joystick 0 and 1)
- `player1` is an AI sprite that moves toward the midpoint of missile0 and missile1
- `player0` is the stationary objective sprite
- `ball` is only used for the temple easter egg in `ROOM_BOTTOM_LEFT`
- Game ends when `player1` reaches the same x/y position as `player0` in the same room
- Touching the temple ball triggers the easter egg, swaps the `player1` sprite art, and uses `_Easter_Egg_Melody` instead of `_Victory_Melody`
- Game over freezes play and cycles the room colors through 9 presets
- Title screen is active until either fire button is pressed
- Title screen plays two-voice music:
  - `_Title_Bass` on channel 1 (`AUDV1`/`AUDC1`/`AUDF1`)
  - `_Title_Melody` on channel 0 (`AUDV0`/`AUDC0`/`AUDF0`)
  - `_Title_Melody_2` is the second melody section, also on channel 0
  - Bass phrase is 512 frames
  - Each melody phrase is 128 frames
  - Melody section 1 plays 4 times, then melody section 2 plays 4 times, then the title song restarts

## Collision Detection — Two Separate Systems

**1. Missile-wall collision (manual, using `pfread`):**
Wall collision is NOT done with the hardware `collision()` function. Instead, the code manually calculates the missile's playfield grid coordinates and calls `pfread(x, y)` to check if a wall pixel is set before allowing movement. This happens every frame in the joystick input section (bank 1).

The coordinate math:
- Playfield x column: `(screen_x - PF_SCR_X_OFFSET) / 4`
- Playfield y row:    `(screen_y - PF_SCR_Y_OFFSET) / 8`
- Both leading and trailing edges of each missile are checked before a move is allowed.

**2. Player1/Player0 game-over collision (position comparison, not hardware):**
```
if p0_room_number = p1_room_number && player1x = player0x && player1y = player0y then goto _start_game_over
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
- `bally` is `TEMPLE_BALL_Y` only in `ROOM_BOTTOM_LEFT`, otherwise `OFFSCRN_Y`
- finding the easter egg immediately hides the ball for the rest of that run

## Playfield Drawing — Runtime `playfield:` Updates

Room walls are currently stored as `playfield:` blocks inside the bank 2 room init routines, not as `pfclear` + `pfhline`/`pfvline`/`pfpixel`.

Why this still works with collision:
1. Each room transition jumps into bank 2 and rewrites the active playfield RAM for the destination room
2. `pfread()` always checks that current playfield RAM, so collision stays aligned with the visible room
3. The title screen also uses a `playfield:` block, but only for the title layout

`maze.txt` matches all 9 gameplay room `playfield:` blocks exactly once the legend markers are ignored.

## Bank Switching Structure

- `set romsize 8k` — 2 banks of 4K each
- **Bank 1:** everything that runs every frame (input, AI, p0/p1 logic, game-over, title loop, boundary-check dispatch stubs)
- **Bank 2:** room setup routines (`_room_right`, `_room_middle`, `_room_left`, `_room_top`, `_room_bottom`, and corner rooms) — only run on room transitions
- `_inititial_game_room` is the startup entry point for the `ROOM_RIGHT` playfield/data and is also used when starting a new game

Each bank 2 room routine ends with `goto _end_boundary_check bank1` to return to the main loop.

**Cost:** `goto bankN` = 49 cycles. Keep cross-bank jumps to a minimum (currently: once per room transition frame, which is acceptable).

**Important:** Data tables can only be accessed from within the same bank they are defined in.
That means free ROM in bank 2 cannot directly hold title music streams read every frame by bank 1 with `sread()` unless the playback design is changed to explicitly bank-switch around that data.

## Room Logic

- Room transitions are decided in the bank 1 boundary-check section
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
```

Connections (implemented):
```
ROOM_RIGHT <-> ROOM_MIDDLE  (left/right doorway)
ROOM_MIDDLE <-> ROOM_LEFT   (left/right doorway)
ROOM_MIDDLE <-> ROOM_TOP    (top/bottom doorway)
ROOM_MIDDLE <-> ROOM_BOTTOM (top/bottom doorway)
ROOM_TOP    <-> ROOM_TOP_RIGHT
ROOM_LEFT   <-> ROOM_TOP_LEFT
ROOM_BOTTOM <-> ROOM_BOTTOM_LEFT
ROOM_BOTTOM <-> ROOM_BOTTOM_RIGHT
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
```

## Editing Guidance

- **ROM space is tight.** Prefer small, targeted changes. Check `.cache/bB.asm` and `.lst` after building to monitor bank usage.
- Title music bytes are constrained by bank 1. Bank 2's free space is not directly available for `_Title_Bass`, `_Title_Melody`, or any future `_Title_Melody_3` table unless the playback code is redesigned around bank switching.
- When adding a room: update bank 1 boundary routing AND add the room init block in bank 2
- When adding a room connection: update the boundary check for both rooms involved
- When changing room geometry: keep `maze.txt` and the matching 32×11 `playfield:` block in sync
- Keep sprite colors readable against each room's background/playfield colors
- There are currently no free registers; all new variable aliases must reuse an existing register only when the usage does not overlap
- Do not reuse `u`/`v` or `w`/`x` for frame-to-frame state while title music is active; they are `sdata` pointers
- Temp variables (`temp1`–`temp6`) are safe to re-alias within a block but are reset by `drawscreen` — never rely on them across frames
- Do not use `collision()` for wall detection — the manual `pfread()` system is intentional and required for the coordinate-based approach
