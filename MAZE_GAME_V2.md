# MAZE_GAME_V2

## Purpose

This file captures requirements, design goals, and open questions for a larger `v2`
of the maze game built around the newer `32k` ROM budget.

The current `maze_game_v2.26b` file is only a prototype for generic missile-based
room transitions. This document is the design target for the fuller game.


## High-Level Goals

- Keep the core fantasy: guide the little red square back to the blue house.
- Expand the maze well beyond the original layout.
- Support longer songs and richer audio sequences.
- Support sound effects.
- Add obstacle-pushing gameplay so rooms are not just navigation puzzles.
- Use a generic room graph instead of hardcoding transition rules room-by-room.
- Allow special rooms with hazards, surprises, or controlled randomness.


## Core Gameplay Pillars

- Navigation through a large interconnected maze.
- Cooperative control using `missile0` and `missile1`.
- Indirect steering of the red square by moving the two missile cursors.
- Puzzle solving through obstacle placement and obstacle movement.
- Room-to-room discovery, including hidden or unusual spaces.


## V2 Requirements

### 1. Generic Room Transition System

- Room transitions should be graph-driven instead of having custom transition code
  for each room.
- Each room should define its neighbors by direction:
  - left
  - right
  - up
  - down
- No separate "blocked edge" concept is required.
- The active playfield remains the source of truth for whether the missiles can
  physically reach an edge.
- If both missiles reach an edge and that direction has a valid destination room,
  the game transitions and redraws the new playfield underneath them.

### 2. Larger Maze

- The maze should be substantially larger than the original.
- It should be more complicated than a `6x6` maze.
- The room graph should support:
  - non-rectangular layouts
  - dead ends
  - loops
  - shortcuts
  - hidden rooms
  - puzzle-gated progress

### 2a. Meaningful Room Names

- Room names should eventually be based on a room's identity, theme, or landmark,
  not just its physical location in the graph.
- Temporary names like `TOP_LEFT`, `MIDDLE`, and `BOTTOM_RIGHT` are useful during
  prototyping, but they should not be the long-term naming scheme.
- A likely direction is to name rooms after places visited with Mom while going to
  see Aunt Terri in Terre Haute.
- The graph/data model should support renaming rooms without needing the names to
  encode their map position.

### 3. Longer Songs

- `v2` should support much longer songs than the original game.
- Music should no longer be constrained by the old `8k` layout assumptions.
- Design should allow:
  - longer title music
  - longer victory music
  - room-specific cues or themes
  - special music for hazards or hidden areas
  - sound effects:
    - ball sprite bouncing off the walls
    - while moving obstacles
    - ball sprite contact with little red square

### 4. Obstacle System

- Rooms can contain obstacles that block the missiles and/or the red square.
- Each room supports at most one obstacle.
- Some obstacles should be movable by one missile but not the other.
- Example rule types:
  - movable by `missile0` only
  - movable by `missile1` only
  - movable by either missile
  - immovable
- Obstacles should create real pathing puzzles, not just decoration.

### 5. Hazard / Randomness System

- The `ball` sprite may be used to create hazard or randomness mechanics.
- At least one room idea:
  - a bouncing ball moves around inside the room
  - it reflects off playfield walls
  - if it hits the little red square, the red square resets to that room's start
    position
- The ball could also support:
  - pressure-style timing rooms
  - patrol hazards
  - random nuisance behavior
  - moving puzzle elements


## Object Roles in V2

### Missiles

- `missile0` and `missile1` remain the two directly controlled objects.
- They are used for:
  - movement through the maze
  - guiding the red square
  - pushing or manipulating obstacles
  - triggering room transitions

### Red Square

- The red square remains the main character the players are trying to rescue or
  guide.
- In the original game this was Terri / `player1`.
- In `v2`, this should remain the primary objective sprite or equivalent object.

### House

- The blue house remains the destination.
- In the original game this was `player0`.

### Obstacle

- Current idea: use `player0` as the obstacle sprite.
- Important consequence: if `player0` is the obstacle in a room, then the blue
  house cannot also be visible in that same room unless the house is represented
  some other way.

This creates a design decision:

- Option A: the house only appears in the final destination room, while `player0`
  is reused as an obstacle in all other rooms.
- Option B: the house becomes part of the playfield art in some rooms.
- Option C: the obstacle is represented differently and `player0` stays reserved
  for the house.

This is an open design choice that should be decided before obstacle-heavy rooms
are implemented.

### Ball

- The ball is a limited primitive but still useful.
- Good uses are simple moving hazards or simple stateful markers.
- The ball should be treated as a gameplay device, not as detailed art.


## Obstacle Rules Draft

Each room may define an obstacle record with fields like:

- obstacle present or absent
- obstacle starting x/y
- obstacle movement type
- obstacle collision type
- obstacle reset behavior

Possible movement types:

- `OBSTACLE_NONE`
- `OBSTACLE_FIXED`
- `OBSTACLE_PUSH_M0`
- `OBSTACLE_PUSH_M1`
- `OBSTACLE_PUSH_BOTH`

Possible room interactions:

- obstacle blocks missile movement
- obstacle blocks red-square movement
- obstacle must be moved onto a parking spot
- obstacle opens a route to a doorway
- obstacle protects the red square from a hazard


## Hazard Room Draft

### Bouncing Ball Room

Core behavior:

- Ball has x/y position and x/y velocity.
- Each frame it attempts to move.
- Before moving, it checks the next playfield cell(s).
- If it would hit a wall, it reverses horizontal or vertical direction.
- If it hits the red square, the red square resets to the room's start position.

Potential extensions:

- Ball speed increases after a delay.
- Ball pauses at corners for dramatic timing.
- Ball pattern is deterministic in some rooms and semi-random in others.


## Audio Ideas

- Longer title theme with multiple phrases.
- Hidden-room or secret-area music.
- Obstacle-solved stinger.
- Hazard-room tension loop.
- More distinctive ending music.

Possible implementation directions:

- dedicate one or more banks mostly to music data
- separate music playback code from room logic
- allow per-room music selection flags


## Room Data Model Draft

Each room should eventually be described by data, not mostly by custom code.

Minimum room data:

- room id
- room name / landmark name
- left destination
- right destination
- up destination
- down destination
- color pair
- playfield loader label
- room entry positions for left/right/up/down
- room start position for the red square
- optional obstacle definition
- optional hazard definition
- optional music id


## Engine Structure Goals

### Bank 1

- joystick input
- missile movement
- playfield collision checks
- generic edge detection
- red-square movement logic
- obstacle interaction logic
- hazard updates if they must run every frame
- audio playback driver

### Other Banks

- room graph / room metadata
- playfield loaders
- music data
- hazard setup data
- scripted events or special room behavior


## Open Questions

1. If `player0` is reused as an obstacle, what should represent the house in the
   final room or in any room where both are needed?

2. Should obstacle movement be tile-based, pixel-based, or snapped after motion?

3. Should the red square reset only within the current room after hazard contact,
   or should some hazards send it farther back?

4. Should ball hazards be deterministic or partially random?

5. Do we want a strictly authored maze, a graph assembled from room templates, or
   a mix of both?

6. Should long music tracks be stored as compact event streams, phrase loops, or
   both?


## Suggested Build Order

1. Finalize the generic room graph structure.
2. Add red-square movement and room persistence on top of the generic transition
   system.
3. Define a room metadata format for starts, colors, and special flags.
4. Add one obstacle type and prove pushing works.
5. Add one hazard room using the ball.
6. Add longer music support.
7. Expand the room set and maze complexity.
8. Add secrets, hidden rooms, and special-case set pieces.


## First Playable V2 Milestone

The first meaningful milestone should include:

- generic room transitions
- red square following behavior
- a larger multi-room maze
- at least one obstacle puzzle
- a visible destination house
- one longer music track
