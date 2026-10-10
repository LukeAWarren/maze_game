# batari Basic (bB) Command Reference

Project quick reference, reviewed **2026-10-10**. Scope: Rescue Terri's standard kernel, with selected other-kernel notes; this is not a complete language manual.

Sources:

- [Upstream source at `efd6dcd319c31a5e37afb00d47c981105998d924`](https://github.com/batari-Basic/batari-Basic/tree/efd6dcd319c31a5e37afb00d47c981105998d924): `keywords.c`, `statements.c`, `preprocess.lex`, and `includes/` are authoritative for this installed build.
- [Latest release, v1.9](https://github.com/batari-Basic/batari-Basic/releases/tag/v1.9).
- [batari Basic command manual](https://www.randomterrain.com/atari-2600-memories-batari-basic-commands.html), linked by the upstream README.

The current master still reports `v1.9 (c)2025`, but includes post-release features such as `autodim` and `variable++`/`variable--`, plus parser/function fixes. The original v1.9 release binaries do not include all of these. This project's active WebAssembly compiler was rebuilt from the revision above; native executables match that source too. Recheck upstream before claiming a later installation is current.

All commands used by `rescue_terri.26b` and its five fragments remain supported. Existing `a = a + 1` arithmetic remains current syntax; adopting every new optional feature is unnecessary. The game keeps explicit RAM aliases, standard-kernel playfield collision, and BCD score arithmetic.

Short examples below sometimes omit leading whitespace. In real BASIC files, indent commands and data lines; put labels and block-ending `end` at the left margin, as in the game sources.

---

## Variables & Memory

### Variables
- 26 single-byte variables: `a` through `z` (values 0–255)
- 6 temporary variables: `temp1`–`temp6` — **clobbered by `drawscreen`, not reset to a guaranteed value**. Library routines may also use them.
- Playfield variables: `var0`–`var47` alias playfield storage; `var44`–`var47` overlap the default hidden row. `pfclear`, scrolling, and 12-row playfield loads can overwrite them.
- Superchip supplies 128 cartridge RAM bytes and relocates playfield storage, freeing the 48 base-RAM playfield bytes for general use. It requires an SC ROM configuration and appropriate cartridge/emulator support; the game currently uses plain `16k`.

### `const`
Declare a compile-time constant (cannot change at runtime). Constants and `dim` aliases share a 500-entry declaration table with generated definitions; leave room for compiler setup instead of treating 500 as an independent constant budget.
```
const _MYCONST = 200
const _MONSTER_HEIGHT = $12
```
Convention: use `SCREAMING_SNAKE_CASE` with a leading underscore (e.g. `_M_TOP_EDGE`).

### `dim`
Create a descriptive alias for a variable. Aliases don't use ROM space.
```
dim _Monster_xpos = a
dim _Monster_ypos = b
dim _Flying_Pickle = f
```
- First char: letter or underscore
- Subsequent chars: letters, numbers, underscores
- **No dots.** Must not match a bB keyword or internal label.
- Multiple aliases can map to the same variable (useful for reuse in different contexts).
- Recommended convention: one underscore prefix + CapitalizedWords → `_Flying_Cat_Data`
- Labels: two underscores prefix → `__My_Label`

### `def`
Like `dim` but defines a string replacement (search & replace at compile time). Useful for bit aliases.
```
dim _Game_Flags = a

def _Game_Level=_Game_Flags & $0F
def _Show_Title=_Game_Flags{4}
def _Game_in_Play=_Game_Flags{5}
def _Game_Over=_Game_Flags{6}
```
- Both `def _Ready=_Flags{4}` and `def _Ready = _Flags{4}` compile with the current preprocessor.
- Keep fewer than 500 definitions; names and replacement strings are limited to 99 characters in the current compiler.
- Strings must be unique (no prefix collisions)

### `autodim` (post-v1.9-release master)
Allocate aliases consecutively inside a RAM range you explicitly reserve:

```
  autodim init a z
  autodim byte _Counter
  autodim byte _Buffer 4
  autodim 4.4 _Fraction
  autodim 8.8 _Position
```

Types are `byte`, `4.4` (one byte each), and `8.8` (two bytes each). The optional count defaults to 1; the end address is inclusive. Assembly fails if allocations exceed the range. This does not detect overlap with other `dim` aliases or make more RAM available. Rescue Terri already assigns a–z, so do not add this example to the game without redesigning its RAM map.

### Increment/decrement (post-v1.9-release master)

```
  _Counter++
  _Counter--
```

These are standalone byte operations, compiled as 6502 `INC`/`DEC`; they wrap at 255/0. Use ordinary arithmetic for the BCD score (`score = score + 1`) and fixed-point values. They are optional shorthand, not a replacement for general expressions. Verify generated code when converting existing logic.

### Bit Operations
Access individual bits with curly braces (bit 0 = rightmost/LSB, bit 7 = leftmost/MSB):
```
a{0} = 1           ; set bit 0
a{2} = !a{2}       ; toggle bit 2
if a{0} then ...   ; check bit is 1
if !a{0} then ...  ; check bit is 0
```
Note: do **not** use `= 0` or `= 1` in if-then for bits; use `if a{0}` / `if !a{0}`.

---

## Control Flow

### `goto`
Jump to a label or line number.
```
goto __My_Label
goto 100
```
Cross-bank (bankswitched games):
```
goto __Move_Monster bank2
```
**Cycle cost:** `goto` = 3 cycles; `goto` with bankswitch = 49 cycles.

### `gosub` / `return`
Call a subroutine and return. Standard-kernel stack space is limited; three nested same-bank calls is the usual conservative limit, not a universal limit for every kernel. Bankswitched calls use additional stack bytes. Avoid deep nesting, especially around `drawscreen`.
```
gosub __My_Subroutine
...
__My_Subroutine
   a = a - 1
   return
```
Cross-bank:
```
gosub __Move_Monster bank2
```
**Cycle cost:** `gosub + return` = 12 cycles; with bankswitch = 122 cycles; with `return otherbank` = 110 cycles.

#### `return thisbank`
Returns only within the current bank. Faster. Will crash if called from another bank.

#### `return otherbank`
Returns to whichever bank called the subroutine. Use when called from different banks.

#### `pop`
Cancels the last gosub's return address, making it behave like a goto.

### `on…goto`
Case-like jump based on variable value (0-indexed):
```
on _Walk_Up goto __P0U0 __P0U1 __P0U2 __P0U3
```
Equivalent to `if _Walk_Up = 0 then goto __P0U0` ... etc.

- Cannot use expressions: `on _Walk_Up-8 goto ...` is **invalid**
- Workaround: `_My_Temp = _Walk_Up - 8 : on _My_Temp goto __P0U0 __P0U1 __P0U2 __P0U3`
- Guard against out-of-range: `if _Walk_Up < 4 then on _Walk_Up goto __P0U0 __P0U1 __P0U2 __P0U3`
- Limit: ~45 labels per statement; break into multiple statements if needed
- **Can only jump within the current bank.** Bankswitching workaround:
```
goto __Color_Fun bank2
...
bank 2
__Color_Fun
   on _Walk_Up goto __Red __Green __Blue __Purple
```

### `on…gosub`
Same as `on…goto` but returns control after the subroutine's `return`.
```
on _Walk_Up gosub __P0U0 __P0U1 __P0U2 __P0U3
drawscreen
```
Same restrictions and workarounds as `on…goto`.

### `if-then` / `if-then-else`
```
if x > 10 then goto __Sink_Ship
if joy0fire then a = a + 1 : b = b - 1
if x = 5 then a = 1 else a = 0
```

### `for` / `next` / `step`
```
for x = 1 to 10
   ...
next
for x = 10 to 1 step -1
   ...
next
```

### `reboot`
Restart via the ROM reset vector. Rescue Terri uses this for the console Reset switch:

```
  if switchreset then reboot
```

## ROM Data and Music Streams

### `data` and indexed access

```
  data _Pitches
  26,17,19,23
end
  a = _Pitches[b]
```

The index is a byte. Keep tables and their readers in the same accessible bank.

### `sdata` / `sread`

```
_setup_stream
  sdata _Notes = u
  26,17,19,255
end
  a = sread(_Notes)
```

`sdata _Notes = u` reserves `u` and the following byte `v` as a pointer. Executing that setup initializes the pointer and skips over the ROM bytes. Every `sread(_Notes)` reads one byte and advances the pointer, including across a 256-byte page. Re-enter the setup to rewind; there is no automatic end marker or bounds check. `255` is a sentinel chosen by the game.

Rescue Terri reserves `u/v` for bass and `w/x` for all melody variants. Each melody setup assigns the same `w/x` pointer; `_Title_Melody` reads whichever stream was selected. Keep the reader and stream data together in bank 3, where this project now places all music.

### `rand` / `rerand`

```
  a = rand
  rerand
```

`rand` supplies a random byte. `rerand`, added in v1.9, advances the generator without assigning a result. Neither is needed by the current game's deterministic movement or music.

---

## Playfield Commands

The playfield is a 32×11 grid (columns 0–31, rows 0–10; row 11 is hidden, used for scrolling).

### `playfield:`
Define a static playfield in source. `X` = pixel on, `.` = pixel off.
```
playfield:
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
X..............................X
X...XXXXXXXXXX....XXXXXXXXXX...X
X..............................X
XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
................................
end
```
- In bankswitched standard kernel: playfield data is stored in whatever bank it's defined in.
- Multisprite kernel: stored in last bank automatically.

### `pfclear`
Clear all playfield pixels (set to off).
```
pfclear
```
Optionally fill with a value:
```
pfclear %10101010
```
**Warning:** Does not work with the multisprite kernel.

To clear without resetting var44–var47 (extra variables on hidden row 11), use a manual approach instead of `pfclear`.

### `pfpixel` — set a single pixel
**Syntax:** `pfpixel xpos ypos function`
- `xpos`: 0–31
- `ypos`: 0–11 (11 is hidden)
- `function`: `on`, `off`, or `flip`
- **Cost:** about 80 cycles per call

```
pfpixel 16 2 on
pfpixel 8 4 off
pfpixel 24 8 flip
```
No bounds checking — exceeding limits may crash the program.

### `pfhline` — draw a horizontal line
**Syntax:** `pfhline xpos ypos endxpos function`
- `xpos`: start column (0–31)
- `ypos`: row (0–11)
- `endxpos`: end column — **must be greater than xpos**
- `function`: `on`, `off`, or `flip`
- **Cost:** approximately 210 + 42 × length cycles per call

```
pfhline 0 0 31 on     ; full-width top wall
pfhline 4 2 8 off
pfhline 2 8 24 flip
```
No bounds checking.

### `pfvline` — draw a vertical line
**Syntax:** `pfvline xpos ypos endypos function`
- `xpos`: column (0–31)
- `ypos`: start row (0–11)
- `endypos`: end row — **must be greater than ypos**
- `function`: `on`, `off`, or `flip`
- **Cost:** approximately 200 + 34 × length cycles per call

```
pfvline 0 0 10 on     ; full-height left wall
pfvline 31 4 8 off
pfvline 8 2 4 flip
```
No bounds checking.

### `pfscroll` — scroll the playfield
```
pfscroll left
pfscroll right
pfscroll up
pfscroll down
pfscroll upup      ; scroll up by 2 vertical steps, not 2 full playfield rows
pfscroll downdown  ; scroll down by 2 vertical steps
```
- `left` / `right`: 500 cycles per call
- `up` / `down`: 650 cycles every 8th call, 30 cycles otherwise
- Row 11 (hidden) is used as source when scrolling up/down — useful for varying backgrounds
- Does **not** work with the multisprite kernel

### `playfieldpos`
Internal variable that tracks which row the playfield starts drawing from. Updated automatically by `pfscroll`. Can be set manually:
```
playfieldpos = 8   ; reset scroll to normal for 32×11 playfield
playfieldpos = 4   ; scroll 4 lines (half a row)
```

### `pfread` — read a playfield pixel state
**Syntax:** `if pfread(xpos, ypos) then ...`
- `xpos`: 0–31, `ypos`: 0–11
- Only valid inside an `if-then` statement
- Can use variables or arrays as arguments

```
if pfread(10,8) then goto __Star_Doink
if !pfread(a, b) then goto __Higher_Frequency_Manifesting
```
For multisprite kernel: use `inline pfread_msk.asm` (must be in last bank). Y-values are reversed in multisprite mode.

---

## Collision Detection

**Important:** Place `drawscreen` **before** collision checks — the hardware must render the frame before collision registers are updated.

**Syntax:** `if collision(object1, object2) then ...`

Valid objects: `playfield`, `ball`, `player0`, `player1`, `missile0`, `missile1`

Objects can be in any order:
```
if collision(playfield, player0) then a = a + 1
if !collision(player0, missile1) then goto __Polly_Tricks
```

- Hardware-based, pixel-perfect
- Multisprite kernel: player2–player5 are virtual and not valid collision arguments; check y-position after `collision(player1,...)` to determine which virtual sprite was hit

---

## Display

### `drawscreen`
Executes the kernel to render the current frame. Must be called regularly within timing constraints.
- Standard kernel: ~2380 cycles per frame budget
- Place before collision detection code

### Sprites
```
player0:
  %00100010
  %01110111
  %01111111
end
player0x = 77
player0y = 53
```

```
player1:
  %11110000
  %10010000
end
player1x = 100
player1y = 45
```

### Missiles & Ball
```
missile0x = 100
missile0y = 20
missile0height = 3    ; height in pixels minus 1
NUSIZ0 = %00100000   ; missile width: 4 pixels

missile1x = 100
missile1y = 75
missile1height = 3
NUSIZ1 = %00100000

ballx = 100
bally = 50
ballheight = 3
```

### Colors
```
COLUBK = $00         ; background color
COLUP0 = $84         ; player0 + missile0 color
COLUP1 = $4A         ; player1 + missile1 color
COLUPF = $0E         ; playfield + ball color
scorecolor = $9C     ; score color (must set for score to appear)
```

### Score
```
score = 100          ; set score (0–999999, BCD format)
const noscore = 1    ; hide score display
const scorefade = 1  ; enable score fade/shading effect
```

---

## Bankswitching

### Overview
The Atari 2600 can only address 4K at a time. Bankswitching swaps in additional 4K banks.

**To enable:** set romsize to 8K or larger.

**Key rules:**
- One bank cannot access data from another bank
- Data tables (arrays) must be in the same bank as the code that reads them
- Sprite graphics are automatically placed in the last bank
- The kernel is always placed in the last bank
- Standard kernel playfield data goes in whatever bank it's defined in
- `goto` and `gosub` can cross banks; `return` auto-returns to the calling bank
- Limit cross-bank jumps — they cost 49 cycles (goto) or 122 cycles (gosub+return)

### `set romsize`
```
set romsize 4k    ; default, no bankswitching
set romsize 8k    ; 2 banks
set romsize 16k   ; 4 banks
set romsize 32k   ; 8 banks
set romsize 64k   ; 16 banks
```
SC variants add Superchip RAM:
```
set romsize 8kSC
set romsize 16kSC
set romsize 32kSC
set romsize 64kSC
```

### Bank Templates

```
; 8K (2 banks)
set romsize 8k
   [bank 1 code]
bank 2
   [bank 2 code]
```

```
; 16K (4 banks)
set romsize 16k
   [bank 1 code]
bank 2
   [bank 2 code]
bank 3
   [bank 3 code]
bank 4
   [bank 4 code]
```

**Note:** Specifying `bank 1` is unnecessary (bank 1 always starts at the beginning).

**Note:** `bank 2` in a bank declaration has a **space** between `bank` and the number.
When used as a destination in `goto`/`gosub`, it has **no space**: `goto __Label bank2`.

### Cross-bank jumps
```
goto __Move_Monster bank2
gosub __Helper bank3
```

### Return variants
```
return            ; auto-detects calling bank (most overhead)
return thisbank   ; return within same bank only (faster, crashes if called from other bank)
return otherbank  ; return to the calling bank (faster for cross-bank, slower for same-bank)
```

### `on…goto` / `on…gosub` bankswitching workaround
These can only jump within the current bank. Workaround:
```
goto __Color_Fun bank2
...
bank 2
__Color_Fun
   on _Walk_Up goto __Red __Green __Blue __Purple
```

---

## Sound

```
AUDC0 = 4    ; channel 0 waveform/control
AUDF0 = 10   ; channel 0 frequency
AUDV0 = 8    ; channel 0 volume

AUDC1 = 4
AUDF1 = 20
AUDV1 = 8

; mute:
AUDV0 = 0 : AUDV1 = 0
```

---

## Input

### Joystick
```
joy0up    joy0down    joy0left    joy0right    joy0fire
joy1up    joy1down    joy1left    joy1right    joy1fire
```
```
if joy0up then player0y = player0y - 1
if !joy0fire then fire_held = 0
```

### Console Switches
```
switchreset     ; reset button
switchselect    ; select button
switchbw        ; color/BW switch
switchleftb     ; left difficulty switch
switchrightb    ; right difficulty switch
```

---

## Miscellaneous

### `asm` / `end`
Inline 6502 assembly:
```
asm
LDA #0
STA a
STA b
end
```

### `rem`
Comment (also `;` works):
```
rem This is a comment
; This is also a comment
```

### Compiler Directives (`set`)
```
set kernel DPC+       ; use DPC+ kernel
set tv ntsc           ; default timing; the game uses this implicitly
set romsize 8k        ; ROM size
```

Standard kernel is the default when no `set kernel` is present. `set kernel PXE` is also available in v1.9 for PXE hardware; switching kernels changes graphics, RAM, and banking requirements and is not a routine update for this game. `set tv pal` changes frame timing, so the game's 60-frame timers and music would need review.

### Kernel Options (`const`)
```
const noscore = 1         ; hide score
const pfres = 4           ; alternate playfield RAM row count
const pfrowheight = 7     ; row height in standard-kernel vertical units
const pfscore = 1         ; enable pfscore bars
const scorefade = 1       ; enable score fade shading
```

`pfres` does not inherently require Superchip; it changes playfield RAM use and display geometry. Check the kernel memory map before increasing it. These examples are independent options, not Rescue Terri's configuration. Graphics options such as `no_blank_lines` use `set kernel_options ...`, not `const`.

### `include`
Include an external assembly module:
```
include div_mul.asm    ; provides multiplication/division support
include 6lives.asm
```

`include` selects assembly modules. `inline` inserts assembly at the current point. Neither concatenates BASIC fragments; this project's `build.sh` combines those in an explicit order.

### Approximate Cycle Count Summary
Historical estimates from the command manual; actual cost depends on generated code, kernel, and bank-return path. Per-call costs become per-frame costs only when called once each frame.
| Operation | Cycles |
|---|---|
| `goto` | 3 |
| `goto` with bankswitch | 49 |
| `gosub + return` | 12 |
| `gosub` with bankswitch `+ return` | 122 |
| `gosub` with bankswitch `+ return otherbank` | 110 |
| `pfpixel` | ~80 / call |
| `pfhline` (length n) | ~210 + 42n / call |
| `pfvline` (length n) | ~200 + 34n / call |
| `pfscroll left/right` | 500 / call |
| `pfscroll up/down` | 650 every 8th call, 30 otherwise |
