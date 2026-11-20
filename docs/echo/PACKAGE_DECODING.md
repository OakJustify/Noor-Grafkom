# Structured LIMBO package decoding

`echo_game/package_data.py` reads two packages from the caller-supplied
installation and writes [`packaged-obstacle-data.json`](packaged-obstacle-data.json).
It does **not** launch LIMBO, recover executable script semantics, load level
assets, copy art/audio, or change ECHO's physics, levels, game or pilot.

The report preserves complete selected declaration lists, their eleven raw
fields, string/field/signature byte ranges, opaque IDs, package/member SHA-256,
decoded-byte coverage, and hashes/ranges of undecoded tails. Every byte range is
half-open (`start` included, `end` excluded); absolute offsets refer to package
bytes, while member offsets begin at zero. Table indices are zero-based;
chapter numbers are the numbers in literal `chapterN` keys. They are not an
established chapter-to-checkpoint mapping.

## Reproduce

```bash
.venv-echo/bin/python -m echo_game.package_data \
  /home/podistrict/Games/LIMBO-SteamRIP.com/LIMBO \
  --output docs/echo/packaged-obstacle-data.json

.venv-echo/bin/python -m pytest -q tests_echo/test_package_data.py
```

The normal tests use only synthetic bytes and the saved JSON report, not
proprietary fixtures or the installation path. An explicitly selected local
reference can additionally reproduce every selected record/hash:

```bash
LIMBO_REFERENCE_ROOT=/home/podistrict/Games/LIMBO-SteamRIP.com/LIMBO \
  .venv-echo/bin/python -m pytest -q tests_echo/test_package_data.py
```

Malformed table ranges, excessive counts, unsupported declaration strings,
and truncated function extensions raise `DecodeError` with member and absolute
offsets. No speculative resynchronization is performed. Unknown text lines are
instead individually ranged and hashed, allowing honest partial text coverage.
The CLI rejects an output path resolving to either input package.

## Artifact identities and table structure

| Package | Bytes | Members | Payload offset |
|---|---:|---:|---:|
| `limbo_boot.pkg` | 20,612,135 | 1,641 | 19,696 |
| `limbo_runtime.pkg` | 12,586,986 | 455 | 5,464 |

```text
limbo_boot.pkg
e7b5128c8ea5251959f6af78f418f89ceb188d8dc2145e3a17afb5ecb8ebbf5f
limbo_runtime.pkg
e5cdd74fb89130f7dd3a5e61e949ad9e38f2962c6d03abaa6b5af09babcb14ff
```

Independent REA `inspect_byte_entropy` identity observations agreed with these
file sizes and full-file hashes:

- Boot: `ev_d93000aa46d499334a6184a1c4e5501155856def6b84cf666faea29877057479`.
- Runtime: `ev_169347c20cf81c74c0291781f794e15df5fd9bd728abd77237bdfe61d1fc5359`.

Those REA observations establish identity, **not** the custom declaration
layout. Their entropy windows covered only the first 4,096 bytes; entropy
does not distinguish compression from encryption. The reproducible Python
decoder and its report establish the structured byte observations below.
Both complete Evidence records are preserved in
[`rea-package-evidence.json`](rea-package-evidence.json); the target-free
investigation was saved and reset after export.

The inferred package layout is:

```text
u32 little-endian member_count
member_count * (u32 opaque_ID, u32 payload_relative_offset, u32 size)
payload starts at 4 + 12 * member_count
member starts at payload_start + payload_relative_offset
```

All 2,096 table ranges were bounds-checked. For these two files, member ranges
have no overlaps or gaps and the final member ends at EOF. The implementation
also handles in-bounds gaps/overlaps without assuming they cannot exist. IDs
are not filenames, resolved script names, or an inferred ID hashing algorithm.
Unselected member index ranges and byte totals remain explicit in the report.

## Declaration-prefix structure

```text
u32 top_declaration_count
top_declaration_count * declaration
u32 local_declaration_count
local_declaration_count * declaration
remaining member bytes: explicitly undecoded tail

declaration:
  u8 name_length;       name_length ASCII bytes
  u8 aux_length;        aux_length ASCII bytes
  u8 annotation_length; annotation_length ASCII bytes
  11 little-endian u32 raw_fields
  if raw_fields[1] == 13:
    u32 argument_count
    argument_count * u32 opaque_type_ID
    u32 return_count
    return_count * u32 opaque_type_ID
```

Strings are restricted to printable ASCII in this observed subset. The
eleven fields remain raw, including values such as `0xffffffff`. Only the
structural `raw_fields[1] == 13` discriminator is used. No calling convention,
type system, field meaning, equation or executed function body is claimed.

### Return-type extension verification

Including both counts aligns both declaration lists in all six selected
members. Boot member 1569 contains four nonempty return lists:

| Declaration name | Argument type IDs | Return type IDs |
|---|---|---|
| `DegreeToRadian` | `[2]` | `[2]` |
| `RadianToDegree` | `[2]` | `[2]` |
| `getPerpendicular` | `[6]` | `[6]` |
| `signedAngleBetweenVectors` | `[6, 6]` | `[2]` |

This is strong **structural support for the inferred count/list extension**,
not native-code verification of its semantic meaning. Other selected function
declarations have empty return lists, but still consume the return-count word.
Synthetic tests include nonempty arguments **and multiple returns**, zero
counts, truncated lists and invalid counts.

### Selected script coverage

Labels below describe declaration vocabulary, not recovered source filenames
or verified execution. Full member hashes and every declaration are in JSON.

| Boot index | Opaque ID | Absolute member start | Size | Top/local declarations | Decoded prefix | Undecoded tail |
|---|---|---:|---:|---:|---:|---:|
| 1518, rope/door | `0xcc9f6936` | 20,395,197 | 2,167 | 19 / 11 | 1,739 | 428 |
| 1566, small gravity | `0xe402b4a8` | 20,512,026 | 429 | 5 / 1 | 345 | 84 |
| 1569, world/boy gravity | `0x9f41be7b` | 20,514,041 | 7,142 | 42 / 51 | 5,748 | 1,394 |
| 1574, water equalization | `0x4200484d` | 20,528,063 | 2,103 | 18 / 9 | 1,671 | 432 |
| 1575, water transfer | `0x8b3cc530` | 20,530,166 | 1,788 | 16 / 8 | 1,464 | 324 |
| 1620, rope generator | `0x25a774d8` | 20,584,092 | 2,362 | 13 / 18 | 1,858 | 504 |

In total: **211 declarations**, **12,825 decoded prefix bytes**, and
**3,166 explicitly undecoded tail bytes** out of 15,991 selected member bytes.
Another 1,635 boot members (20,576,448 bytes) are not decoded.

## Observed annotation defaults — not level-instance values

These defaults and ranges appear literally in declaration annotations. The
report keeps the exact annotation and default text alongside derived numeric
values. They do not prove a level uses these values, determine engine units,
or justify importing them into ECHO's simulation.

| Member | Declaration | Literal annotation |
|---|---|---|
| 1569 | `angle`, `boy_angle` | `0.0,360.0:default=0` |
| 1569 | `rotationSpeed`, `boy_rotationSpeed` | `0.00,4.0:default=0.00` |
| 1569 | `worldStrength`, `strengthSpeed` | `0.0,10.0:default=10.0` |
| 1574 | `areaPerSecond` | `0.0,20.0: default=5.0` |
| 1575 | `areaPerSecond` | `0.0,20.0: default=5.0` |
| 1575 | `easeInTime` | `0.0,2.0: default=0.0` |
| 1620 | `length` | `0.0,100.0:default=4.0` |
| 1620 | `ropeWidth` | `0.0,10.0:default=0.1` |
| 1620 | `numberOfSegments` | `0,200:default=6` |
| 1620 | `segmentDensity` | `0.0,100.0:default=0.25` |
| 1620 | `segmentDrag` | `0.0,10.0:default=0.05` |

The rope/door member also names `moveSpeedUp`, `moveSpeedDown`,
`ropeJointSpring`, `doorJointSpring`, `boyOnRope` and `boyOffRope`, but has no
numeric annotation defaults. The small-gravity member names `gravity`,
`target`, `body`, `start` and `integrate`, also without annotation defaults.
Water members name triggers/handlers and state variables; names alone do not
establish how those handlers execute or how water is simulated.

## Readable runtime records

Member 0 (`0x171c28ea`, absolute bytes `[5464, 8102)`) decodes completely into
**39 chapter mappings**. Examples:

- `chapter1`: `data/levels/start/falling_and_pursuing_boys.branch 1`.
- `chapter24`: `data/levels/city/crane_and_seesaw.branch 1`.
- `chapter35`: `data/levels/modern_underground/magnetgravitytiming.branch 1`.
- `chapter39`: `data/levels/modern_underground/gravity_jump.branch 4`.

All 39 ordered mappings, literal strings and byte ranges are preserved; paths
are not resolved and branch entries are not loaded.

Members **1–102** decode completely into **612 checkpoint fields**: `boydir`,
`boygravity`, `boypaused`, `boypos`, `savepointnode`, and `worldgravity` in each
member. Together with member 0, the selected runtime coverage is **20,844 /
20,844 bytes**, including blank lines and line terminators; no unknown text
regions occur in these selected members. Another 352 runtime members
(12,560,678 bytes, indices 103–454) are not decoded.

Assignments are parsed with anchored simple quoted-ASCII grammar, not literal
searches. Duplicate keys stay ordered rather than silently overwriting one
another. Exact numeric strings remain authoritative; derived scalar/vector
values have explicitly unknown units. Unsupported escapes, malformed lines,
non-ASCII text and unrecognized line endings remain unknown regions.

Observed checkpoint literal counts:

- `boygravity`: `0.000000,0.000000` in all 102 records.
- `boydir`: `1.000000` in 86; `-1.000000` in 16.
- `boypaused`: `false` in 99; `true` in members 96, 97 and 98.
- `worldgravity`: `0.000000,-10.000000` in 94; the other eight are below.

| Runtime member | Exact `worldgravity` string |
|---|---|
| 79 | `0.000002,-10.000000` |
| 80 | `0.000002,-10.000000` |
| 83 | `10.000000,0.000001` |
| 85 | `2.005630,-9.796808` |
| 87 | `-0.524874,9.986216` |
| 88 | `-0.524871,9.986216` |
| 89 | `-0.524866,9.986216` |
| 90 | `0.524863,-9.986216` |

These are **serialized checkpoint values**, not observed runtime acceleration,
a universal gravity default, or evidence that zero boy gravity means zero net
force. The meaning of `savepointnode`, checkpoint indexing and how these fields
affect native engine state are unresolved.

## Remaining unknowns

- The script tails are not decompiled or disassembled and have no recovered
  execution semantics; their bytes are never exported as assets or code.
- Most raw declaration-field meanings and all type-ID semantics remain opaque.
- Original physical units, timestep, integration, collision, buoyancy,
  water-transfer equations, rope constraints and controller behavior remain
  unknown. Annotation vocabulary does not recover those algorithms.
- Level-instance overrides, original obstacle geometry and chapter/checkpoint
  relationships are not recovered.
- Unselected members and their compression/object serialization are not
  decoded. Coverage is complete only for the stated tables and selected
  declaration prefixes/readable records, not the packages or game as a whole.
