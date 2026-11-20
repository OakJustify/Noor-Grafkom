# Concrete LIMBO gameplay references

Researched **2026-11-15**. This is a behavior-reference ledger for ECHO, not a claim that ECHO's rooms reproduce LIMBO checkpoints or that the supplied executable was run.

## Evidence and boundaries

- **Complete relevant pages were fetched and read**, not just search snippets: IGN's detailed LIMBO guide and PortForward's screenshot-by-screenshot walkthrough. HTML response digests, exact short quotations, source URLs, source-local sections, and proposed tests are recorded in [`reference-gameplay.json`](reference-gameplay.json).
- **Twenty actual walkthrough stills were downloaded and visually inspected.** Their original image URLs and SHA-256 values are retained in the JSON. A still establishes visible placement, not movement, input, timing, or cause; those claims below come from explicit guide instructions.
- **No native LIMBO runtime or gameplay video was watched.** Retrieved IGN pages contained empty auto-embed video containers, with no usable gameplay URL found in their inspected Next.js data. No timestamps are invented. Screenshot numbers below are image identifiers, not video frames/times.
- IGN uses **24 guide chapters**; PortForward uses **38 walkthrough pages**. Numbers are publisher-specific, not verified level/checkpoint IDs. Neither establishes which packaged-level name in the supplied artifact corresponds to a room.
- The [official Playdead page](https://www.playdead.com/games/limbo/) establishes product identity and offers a screenshot gallery/trailer, but provides no detailed obstacle instructions. TrueAchievements and StrategyWiki were blocked by HTTP 403 and are **not evidence** here.

## 1. Ropes: climb, swing, transfer, release

Concrete references:

| Source / location | Exact short support |
| --- | --- |
| [PortForward Chapter 2](https://portforward.com/games/walkthroughs/Limbo/Chapter-2.htm), screenshot 10 | “Climb down the rope.” |
| [PortForward Chapter 10](https://portforward.com/games/walkthroughs/Limbo/Chapter-10.htm), screenshot 115 | “Climb up the rope.” |
| [PortForward Chapter 15](https://portforward.com/games/walkthroughs/Limbo/Chapter-15.htm), screenshots 185–186 | “Climb the rope until it stops moving.” / “Then swing and jump to the next rope.” |
| [IGN Chapter 02](https://www.ign.com/wikis/limbo/Chapter_02), vine/achievement paragraph | “Swing from the bottom of the vine in order to jump to a branch on your right” |

**Reported behavior:** Rope/vine traversal is not only angular swinging. The boy can traverse vertically, choose a height, swing, and leave for a ledge or another rope. Chapter 15 also explicitly has the player pull a rope down, release it, re-grab it before it retracts, and transfer to a second rope to pass beneath stone mechanisms.

**Inspected stills:** [10](https://portforward.com/games/walkthroughs/Limbo/limbo-10-small.webp) and [115](https://portforward.com/games/walkthroughs/Limbo/limbo-115-small.webp) show the boy attached along long ropes. [185](https://portforward.com/games/walkthroughs/Limbo/limbo-185-small.webp) and [186](https://portforward.com/games/walkthroughs/Limbo/limbo-186-small.webp) show vertical attachment and a displaced-rope/transfer state. These do not measure climb speed or a swing arc.

**Suggested ECHO acceptance tests:**

1. Grab a reachable point on a long rope. Up/down input changes player height while still attached; it must not merely increase swing amplitude.
2. Climb lower, swing, and release to a ledge or second rope. Release visibly detaches the player; a landing or failure follows without teleporting.
3. Require at least one useful height decision in `ropepit`, so vertical climbing is consequential rather than ornamental.

**Unknown:** Actual build-specific bindings, grab radius, climb speed, attachment-coordinate implementation, and solver. ECHO's controls/tuning must be called design choices.

## 2. Water: positioned wood, rising boxes, and sluice controls

Concrete references:

| Source / location | Exact short support |
| --- | --- |
| [IGN Chapter 09](https://www.ign.com/wikis/limbo/Chapter_09), pipe/log sequence | “Wait for the hole to fill up with water, then quickly jump right across the floating log that you positioned earlier.” |
| [IGN Chapter 10](https://www.ign.com/wikis/limbo/Chapter_10), first paragraph | “jump left to your floating Box as it rises through the gap.” |
| IGN Chapter 10, later box/ball sequence | “The ball will rise under the Box and help you all float up to the next ledge.” |
| [PortForward Chapter 18](https://portforward.com/games/walkthroughs/Limbo/Chapter-18.htm), screenshot 236 | “The key is to let just enough water in so you can jump from the box in the middle to the next box.” |

**Reported sequences—not a universal water rule:**

- **Positioned log:** Put wood in the useful part of a dry hole, hang on the rope to connect the pipe, wait for water, then cross on the floating log. PortForward's [Chapter 17](https://portforward.com/games/walkthroughs/Limbo/Chapter-17.htm), screenshots 209–214, corroborates positioning wood, filling the pit using a chain, releasing, and jumping across.
- **Box lift:** Put a box under an overhead opening, move the cover to expose the gap, flood the room with a lever, and ride the floating box through the gap to the next ladder. The cover and placement are causal dependencies.
- **Later box/ball:** Another box only carries the player until the water reaches its top. A subsequent box is helped upwards by a ball deliberately released, trapped with a cover, and moved underneath it. Do not infer that every wooden object has identical permanent flotation or invent an internal waterlogging model.
- **Balancing water:** Regulate water until adjacent platforms are jumpable; releasing the switch changes a large block's position. The same PortForward paragraph explicitly says the large box “will drop when you release the switch.”

**Inspected stills:** [221](https://portforward.com/games/walkthroughs/Limbo/limbo-221-small.webp) shows a cover with a box below; [222](https://portforward.com/games/walkthroughs/Limbo/limbo-222-small.webp) shows the boy on the box at a higher water surface. [236](https://portforward.com/games/walkthroughs/Limbo/limbo-236-small.webp) and [239](https://portforward.com/games/walkthroughs/Limbo/limbo-239-small.webp) show block platforms and a water jump. Lever effects are textual reports, not inferred from a still alone.

**Suggested replacement for ECHO's propelled raft:** An original **sluice-and-buoyant-box room** is grounded in the above sequence. Position box → expose gap → operate local water control → box rises carrying player → jump to ledge. Its dimensions, water rate, maximum level, and binding are ECHO choices.

**Suggested acceptance tests:**

1. An incorrectly positioned box is blocked by the cover or fails to reach the route. Correct positioning makes the opening useful.
2. Water level and floating-box height visibly change together. The player is carried vertically while standing on the box; directional movement is not a secret platform motor.
3. Low/incorrect water cannot solve a balancing-water variant; sufficient water plus the correctly released block enables its jump sequence.
4. If the ball variant is included, support depends on moving the ball under the box, not boarding it granting propulsion.

### Important distinction: passive boat travel is supported; rowing is not established

[PortForward Chapter 2](https://portforward.com/games/walkthroughs/Limbo/Chapter-2.htm), screenshot 15, says: “The chain will break when you land, and the boat will start to float across the lake.” [IGN Chapter 01](https://www.ign.com/wikis/limbo/Chapter_01) then instructs the player to leave the boat, pull it against a wall, and use it as a step. [PortForward Chapter 4](https://portforward.com/games/walkthroughs/Limbo/Chapter-4.htm), screenshots 57–60, instead has wood pushed into position from shore before the boy climbs onto it and jumps across.

Thus **“LIMBO has passive boat drift”** is supported. **“Left/right input while standing on any raft automatically rows it”** is not supported by these reviewed passages. The internal drift cause remains unknown, and this bounded review does not prove no unreviewed water vehicle exists anywhere in the game.

## 3. Gravity: distinguish three concrete modes and a separate magnet

### A. Manual box-only field and momentum through a gap

[PortForward Chapter 33](https://portforward.com/games/walkthroughs/Limbo/Chapter-33.htm), screenshot 596: “Flicking the switch here reverses gravity for boxes, but not for you.” Its next instructions describe a box sliding on a slope, lifting it through a gap, and preserving speed. [IGN Chapter 21](https://www.ign.com/wikis/limbo/Chapter_21) independently says: “This way the Box keeps its momentum from sliding down the hill and lands at your feet.” Later in that same chapter, a different switch puts the player on the ceiling and requires placing two boxes around a moving ledge.

**Consequence:** Manual switching is authentic to some LIMBO sequences. ECHO's manual relays are not automatically incorrect merely because they are manual; what is missing is a named variant with a concrete object/route/timing dependency.

**Suggested tests:** In a box-only field the boy remains grounded while the box lifts/drops. The ramp supplies horizontal velocity that survives switching. Bad timing collides with the ceiling/floor obstruction; suitable timing carries the box through the gap and turns it into a climbable step.

### B. Magnetic ceiling capture with timed manual gravity

[IGN Chapter 22](https://www.ign.com/wikis/limbo/Chapter_22) instructs the player to magnetize the ceiling, activate gravity until the first block touches it, then “Quickly turn off the Gravity Switch before the second block reaches the ceiling to send it back to the ground.” [PortForward Chapter 34](https://portforward.com/games/walkthroughs/Limbo/Chapter-34.htm), screenshot 632, states the resulting requirement: “The one above you needs to stay up and the one to the right needs to stay down.”

**Concrete mechanic:** The magnet retains a contacted block while the gravity control returns an uncaptured block down. They are independent controls, not two labels for the same gravity boolean. The arrival-time difference creates the timing puzzle.

**Inspected stills:** [630](https://portforward.com/games/walkthroughs/Limbo/limbo-630-small.webp), [631](https://portforward.com/games/walkthroughs/Limbo/limbo-631-small.webp), and [632](https://portforward.com/games/walkthroughs/Limbo/limbo-632-small.webp) show changing block heights and a final split-height arrangement. They do not measure the contact interval or magnetic forces.

**Suggested tests:**

1. Capture first block at the ceiling; restore downward gravity before second contact. First stays high, second returns low, and the intended route becomes reachable.
2. Too early: first never captures. Too late: both capture and the split-height route fails.
3. Magnet-off releases the retained eligible block. Magnet toggling does not itself mean gravity toggling.

### C. Temporary activation, then periodic gravity reversal

[IGN Chapter 23](https://www.ign.com/wikis/limbo/Chapter_23) describes repeated activation of a **timed** switch to move a box incrementally right on the ceiling before the field deactivates. [IGN Chapter 24](https://www.ign.com/wikis/limbo/Chapter_24) says: “Listen to the speeding up sound of beeps for the timed gravity switching here”. It requires exposing/deactivating a magnet just before a reversal to evade gun fire, running across the released block, and timing later jumps between saws.

[PortForward Chapter 37](https://portforward.com/games/walkthroughs/Limbo/Chapter-37.htm) corroborates both waiting for reversal and repeated automatic changes. At screenshot 669: “Wait until gravity is about to reverse, then jump out to the magnetic switch and turn it off.” At screenshot 673: “Gravity will reverse again. Just wait for it to reverse again.”

**Inspected stills:** [669](https://portforward.com/games/walkthroughs/Limbo/limbo-669-small.webp), [670](https://portforward.com/games/walkthroughs/Limbo/limbo-670-small.webp), and [672](https://portforward.com/games/walkthroughs/Limbo/limbo-672-small.webp) show the separate control, large block, and crossing states; the periodic schedule comes from the text.

**Suggested tests:**

1. Temporary mode returns automatically after activation; each successful window preserves useful box relocation while the player retreats to safety.
2. Periodic mode repeatedly inverts gravity without an action for every flip. The player and unrestrained block respond; a held block remains held until the magnet is released.
3. Give a phase cue and demonstrate both successful timing and an early/late failure against the configured hazard or missing support.

**Unknown:** Timer duration, phase-reset policy, gun delay, and physics constants in the supplied build. IGN's approximate beep counts are route advice, **not measured seconds**. An ECHO timer/cue is an explicit adaptation choice.

## 4. Pressure switches: door opening, physical jamming, lifting ledge

[IGN Chapter 16](https://www.ign.com/wikis/limbo/Chapter_16) first states that a Pressure Switch opens a door. Later the player transports a wheel and is told: “Pull it right to the Pressure Switch and jump right through the open door, then quickly pull the Box left to jam the door.” [PortForward Chapter 26](https://portforward.com/games/walkthroughs/Limbo/Chapter-26.htm), screenshot 404, corroborates moving the box through when the wheel triggers the gate.

The later two-box sequence in the same pages is **a different pressure mechanism**: leave one box near the destination, place the second box on the button, and climb the rising ledge using the first. Screenshot 425 says: “Put the second box on the button, and then climb on to the raising platform.”

**Inspected stills:** [400](https://portforward.com/games/walkthroughs/Limbo/limbo-400-small.webp) shows the lower wheel track; [404](https://portforward.com/games/walkthroughs/Limbo/limbo-404-small.webp) shows the box at the upper door; [425](https://portforward.com/games/walkthroughs/Limbo/limbo-425-small.webp) shows the separate box/button lift setup.

**ECHO implication:** `cratepressuregate` is a reduced pressure-switch abstraction, not the complete LIMBO wheel/door sequence. A closer original adaptation can use a closing-door jam or a two-box pressure-lift dependency.

**Suggested tests:** Switch contact visibly opens the actual blocking door. A box left in the opening physically arrests closure rather than being clipped by the gate. In a chosen non-latching adaptation, removing the weight and then removing the jam allows closure. Alternatively, the second box raises a ledge, while the previously positioned first box is needed to reach the exit. Thresholds, closure rates, and crushing rules remain ECHO choices; they are not established by these pages.

## 5. Traps, rolling boulders, falling logs—and a genuine seesaw

### Traps and obstacle naming

[PortForward Chapter 3](https://portforward.com/games/walkthroughs/Limbo/Chapter-3.htm), screenshots 31–35, has the player drag a jaw trap beneath a hanging carcass rope. It says: “The trap will trigger and take the meat off of the end of the rope. Which will raise you up.” [IGN Chapter 03](https://www.ign.com/wikis/limbo/Chapter_03) describes baiting a spider leg onto a repositioned trap so it snaps shut on the leg.

[IGN Chapter 01](https://www.ign.com/wikis/limbo/Chapter_01) describes retreating when a log shifts and a **boulder** tumbles towards the boy. [PortForward Chapter 6](https://portforward.com/games/walkthroughs/Limbo/Chapter-6.htm), screenshot 76, instead says: “Push the boulder forward, and then jump out of the way of the falling log.” These support different sequences. **Do not collapse rolling boulder, shifting support log, and falling log into an asserted LIMBO “rolling log” mechanic.**

**Suggested tests:** A movable armed trap can be positioned safely but touching its jaws triggers the configured lethal response. A carcass/counterweight variant requires loading the rope into the trap; severing the load raises the usable rope. A boulder variant visibly rolls towards the player with a retreat/jump escape; a falling-log variant visibly falls to form the crossing. Trigger thresholds and break/hinge models are unknown.

### Seesaw / oscillating platform

The existing ECHO seesaw has a concrete reference available: [PortForward Chapter 22](https://portforward.com/games/walkthroughs/Limbo/Chapter-22.htm), screenshot 338, says: “This platform is a giant teeter totter. Run back and forth on it until it's really teetering.” [IGN Chapter 13](https://www.ign.com/wikis/limbo/Chapter_13) describes alternating between the edges, building movement over about 6–7 repetitions, and departing at the appropriate phase. The [inspected still 338](https://portforward.com/games/walkthroughs/Limbo/limbo-338-small.webp) shows a tilted suspended/support-connected platform; its exact joint is not established.

**Suggested tests:** Alternating runs/jumps increases motion compared with standing still. A useful phase makes the exit reachable, rather than the beam serving as permanent stairs. Player support/collision remains coherent while tilting. No exact repetition count, damping, joint type, or physics match is claimed.

## Recommended adaptation boundaries

| Original ECHO room | Grounded direction | Do not claim |
| --- | --- | --- |
| `cratepressuregate` | Pressure door with physical box jam, or two-box pressure lift | Exact wheel puzzle/checkpoint equivalence |
| `ropepit` | Vertical climb + useful height choice + swing/release | Pendulum-only swinging covers all LIMBO rope behavior |
| `raft` | Positioned floating wood or sluice-driven box lift; optionally explicit passive boat drift | On-deck movement keys are LIMBO rowing |
| `seesaw` | Build oscillation and leave at a useful phase | Static weighted beam or exact reference joint/constants |
| `gravityrelays` | Identify box-only/manual, capture-magnet, temporary, or periodic variant; give it the corresponding causal dependency | All LIMBO gravity is periodic, all is manual, or magnet = gravity |

These are **proposed tests and designs, not tests already run**. The source ledger separates guide reports, inspected stills, unknowns, and ECHO adaptation choices. Runtime equivalence to the user-supplied artifact still requires separate evidence.
