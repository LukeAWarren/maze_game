# Maze Game Notes

## Build

- Project root: `/Users/luke/code/atari/batari/maze_game`
- Main source: `maze_game.26b`
- Standard compile command: `sh ./build.sh`
- `build.sh` defaults `bB` to `/Users/luke/opt/batari-Basic` and runs `2600basic.sh`
- Current CLI toolchain works in this repo with:
  - batari Basic `v1.9 (c)2025`
  - DASM `2.20.15-SNAPSHOT`

## Build Outputs

- Standard build output location is `bin/`:
  - `bin/maze_game.26b.asm`
  - `bin/maze_game.26b.bin`
  - `bin/maze_game.26b.lst`
  - `bin/maze_game.26b.sym`
- Compiler intermediates are moved into `.cache/`:
  - `.cache/bB.asm`
  - `.cache/2600basic_variable_redefs.h`
  - `.cache/includes.bB`
- If ADS is used directly, it may also refresh files under `bin/`

## Local References

- Use `.cache/bb_commands_reference.md` as the local batari Basic reference
- `include div_mul.asm` is already used by the project (provides multiplication/division)
- `maze.txt` is the full 96×33 room layout reference; each `maze_game.26b` room playfield is a 32×11 slice from it

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
| z | (free) | not yet assigned |

Temp variables `temp1`–`temp6` are used within single logical blocks and reset after `drawscreen`. They are re-aliased at point of use (e.g. `dim mid_delta = temp3`).

## Key Constants

```
; Screen boundaries (missile movement limits)
SCR_LEFT_X  = 18     SCR_RIGHT_X = 142
SCR_TOP_Y   = 4      SCR_BOT_Y   = 87
OFFSCRN_Y   = 200    ; y value used to hide sprites off-screen
SCORE_COLOR = $1C    ; gold score color

; Entry gate positions (where missiles/player1 appear when entering a room)
ENTRY_GATE_LEFT_X  = 22    ENTRY_GATE_RIGHT_X = 138
ENTRY_GATE_TOP_Y   = 8     ENTRY_GATE_BOT_Y   = 79

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
- Game ends when `player1` reaches the same x/y position as `player0` in the same room
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

## Playfield Drawing — pfhline/pfvline/pfpixel vs playfield:

Room walls are drawn with `pfclear` + `pfhline`/`pfvline`/`pfpixel` rather than `playfield:` blocks because:
1. Rooms are drawn dynamically at runtime during room transitions (in bank 2)
2. The same playfield RAM is what `pfread()` reads for collision — it must stay current
3. `pfhline`/`pfvline` is more ROM-efficient than full 32×11 `playfield:` data for simple geometric layouts

The title screen uses `playfield:` because it is a one-time static layout and is never used for collision detection.

## Bank Switching Structure

- `set romsize 8k` — 2 banks of 4K each
- **Bank 1:** everything that runs every frame (input, AI, p0/p1 logic, game-over, title loop, boundary-check dispatch stubs)
- **Bank 2:** room setup routines (`_room_right`, `_room_middle`, `_room_left`, `_room_top`, `_room_bottom`, and corner rooms) — only run on room transitions

Each bank 2 room routine ends with `goto _end_boundary_check bank1` to return to the main loop.

**Cost:** `goto bankN` = 49 cycles. Keep cross-bank jumps to a minimum (currently: once per room transition frame, which is acceptable).

**Important:** Data tables can only be accessed from within the same bank they are defined in.

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

## Editing Guidance

- **ROM space is tight.** Prefer small, targeted changes. Check `.cache/bB.asm` and `.lst` after building to monitor bank usage.
- When adding a room: update bank 1 boundary routing AND add the room init block in bank 2
- When adding a room connection: update the boundary check for both rooms involved
- Keep sprite colors readable against each room's background/playfield colors
- All new variable aliases must map to currently-free registers or reuse an existing register if the usage doesn't overlap
- Do not reuse `u`/`v` or `w`/`x` for frame-to-frame state while title music is active; they are `sdata` pointers
- Temp variables (`temp1`–`temp6`) are safe to re-alias within a block but are reset by `drawscreen` — never rely on them across frames
- Do not use `collision()` for wall detection — the manual `pfread()` system is intentional and required for the coordinate-based approach
