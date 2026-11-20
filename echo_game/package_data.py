"""Read-only, bounded decoding of selected LIMBO package metadata.

This decodes an inferred table/declaration layout, not script execution. No
target is launched and no asset payload or undecoded bytecode is exported.
"""

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
import struct


SCRIPT_SELECTION = {
    1518: "rope/door declarations",
    1566: "small gravity declarations",
    1569: "world/boy gravity declarations",
    1574: "water equalization declarations",
    1575: "water transfer declarations",
    1620: "rope generator declarations",
}
SCHEMA_VERSION = 1
MIN_DECLARATION_BYTES = 3 + 11 * 4
NUMBER = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
ASSIGNMENT = re.compile(rb'[ \t]*([A-Za-z_][A-Za-z_0-9]*)[ \t]*=[ \t]*"([\x20-\x21\x23-\x5b\x5d-\x7e]*)"[ \t]*')
DEFAULT = re.compile(rf"({NUMBER}),({NUMBER}):\s*default=({NUMBER})")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def byte_range(start, end, absolute_start=0):
    """All ranges are half-open and absolute offsets refer to package bytes."""
    return {"member_start": start, "member_end": end,
            "absolute_start": absolute_start + start,
            "absolute_end": absolute_start + end, "size": end - start}


class DecodeError(ValueError):
    def __init__(self, message, member_offset=0, absolute_start=0):
        self.member_offset = member_offset
        self.absolute_offset = absolute_start + member_offset
        super().__init__(f"{message} (member byte {member_offset}, absolute byte {self.absolute_offset})")


class Reader:
    def __init__(self, data, absolute_start=0):
        if not isinstance(absolute_start, int) or absolute_start < 0:
            raise ValueError("absolute_start must be a nonnegative integer")
        self.data = data
        self.absolute_start = absolute_start
        self.pos = 0

    def fail(self, message, offset=None):
        raise DecodeError(message, self.pos if offset is None else offset, self.absolute_start)

    def take(self, size):
        if size < 0 or size > len(self.data) - self.pos:
            self.fail(f"truncated read: need {size} bytes, have {len(self.data) - self.pos}")
        start = self.pos
        self.pos += size
        return self.data[start:self.pos]

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]

    def count(self, minimum_item_bytes, label):
        start = self.pos
        count = self.u32()
        if count > (len(self.data) - self.pos) // minimum_item_bytes:
            self.fail(f"invalid {label} count {count} for remaining bytes", start)
        return count

    def string(self):
        start = self.pos
        length = self.take(1)[0]
        raw = self.take(length)
        if any(c < 32 or c > 126 for c in raw):
            self.fail("string is not printable ASCII", start)
        return raw.decode("ascii"), byte_range(start, self.pos, self.absolute_start)


@dataclass(frozen=True)
class Member:
    index: int
    identifier: int
    payload_relative_offset: int
    size: int
    table_offset: int
    absolute_start: int

    def identity(self, package_data):
        return {"index": self.index, "identifier": self.identifier,
                "identifier_hex": f"0x{self.identifier:08x}",
                "table_absolute_start": self.table_offset,
                "table_absolute_end": self.table_offset + 12,
                "payload_relative_offset": self.payload_relative_offset,
                "absolute_start": self.absolute_start,
                "absolute_end": self.absolute_start + self.size,
                "size": self.size, "sha256": sha256(self.read(package_data))}

    def read(self, package_data):
        return package_data[self.absolute_start:self.absolute_start + self.size]


def decode_package(data):
    """Validate every table range before exposing members (IDs stay opaque)."""
    reader = Reader(data)
    count = reader.count(12, "package member")
    payload_offset = 4 + 12 * count
    members = []
    for index in range(count):
        table_offset = reader.pos
        identifier, offset, size = struct.unpack("<III", reader.take(12))
        absolute_start = payload_offset + offset
        if absolute_start > len(data) or size > len(data) - absolute_start:
            reader.fail(f"member {index} range exceeds package", table_offset)
        members.append(Member(index, identifier, offset, size, table_offset, absolute_start))
    return payload_offset, members


def unknown_region(data, start, end, absolute_start=0):
    return {**byte_range(start, end, absolute_start),
            "sha256": sha256(data[start:end]), "status": "undecoded"}


def annotation_default(annotation):
    match = DEFAULT.fullmatch(annotation)
    if not match:
        return None
    numbers = [float(value) for value in match.groups()]
    if not all(math.isfinite(value) for value in numbers):
        return None
    return {"range_min": numbers[0], "range_max": numbers[1],
            "default_literal": match.group(3), "default_number": numbers[2],
            "scope": "observed declaration annotation; not a level-instance value"}


def declaration(reader, index):
    start = reader.pos
    strings, string_ranges = {}, {}
    for label in ("name", "aux", "annotation"):
        strings[label], string_ranges[label] = reader.string()
    raw_start = reader.pos
    fields = [reader.u32() for _ in range(11)]
    result = {"index": index, **strings, "string_ranges": string_ranges,
              "raw_fields": fields,
              "raw_fields_range": byte_range(raw_start, reader.pos, reader.absolute_start),
              "raw_field_member_offsets": [raw_start + 4 * i for i in range(11)],
              "raw_field_absolute_offsets": [reader.absolute_start + raw_start + 4 * i for i in range(11)]}
    if fields[1] == 13:
        signature_start = reader.pos
        arg_count_offset = reader.pos
        arg_count = reader.count(4, "argument type")
        arg_start = reader.pos
        args = [reader.u32() for _ in range(arg_count)]
        return_count_offset = reader.pos
        return_count = reader.count(4, "return type")
        return_start = reader.pos
        returns = [reader.u32() for _ in range(return_count)]
        result["function_signature"] = {
            "interpretation": "inferred count/type-ID lists; IDs are opaque",
            "argument_count": arg_count, "argument_type_ids": args,
            "argument_count_range": byte_range(arg_count_offset, arg_count_offset + 4, reader.absolute_start),
            "argument_type_ids_range": byte_range(arg_start, return_count_offset, reader.absolute_start),
            "return_count": return_count, "return_type_ids": returns,
            "return_count_range": byte_range(return_count_offset, return_count_offset + 4, reader.absolute_start),
            "return_type_ids_range": byte_range(return_start, reader.pos, reader.absolute_start),
            "byte_range": byte_range(signature_start, reader.pos, reader.absolute_start),
        }
    result["byte_range"] = byte_range(start, reader.pos, reader.absolute_start)
    default = annotation_default(strings["annotation"])
    if default is not None:
        result["annotation_default"] = default
    return result


def decode_script(data, absolute_start=0):
    """Decode both declaration lists; reject malformed counts/strings/extensions.

    Bytes following the local list remain opaque even if they resemble code.
    Invalid members raise DecodeError rather than inventing resynchronization.
    """
    reader = Reader(data, absolute_start)
    result = {"format": "inferred script declaration prefix", "sha256": sha256(data)}
    for scope in ("top", "local"):
        count_start = reader.pos
        count = reader.count(MIN_DECLARATION_BYTES, f"{scope} declaration")
        result[f"{scope}_count"] = count
        result[f"{scope}_count_range"] = byte_range(count_start, count_start + 4, absolute_start)
        result[f"{scope}_declarations"] = [declaration(reader, index) for index in range(count)]
    result["coverage"] = {
        "member_size": len(data), "bytes_decoded": reader.pos,
        "bytes_undecoded": len(data) - reader.pos,
        "decoded_range": byte_range(0, reader.pos, absolute_start),
        "declaration_lists_complete": True, "execution_recovered": False,
    }
    result["unknown_tail"] = unknown_region(data, reader.pos, len(data), absolute_start)
    return result


def interpreted_value(key, value):
    """Derived types for literal fields only, not engine units or runtime state."""
    if key in ("boydir", "boypos", "boygravity", "worldgravity"):
        parts = value.split(",")
        length = 1 if key == "boydir" else 2
        if len(parts) == length and all(re.fullmatch(NUMBER, p) for p in parts):
            numbers = [float(p) for p in parts]
            if all(math.isfinite(n) for n in numbers):
                return {"kind": "serialized_number" if length == 1 else "serialized_vector2",
                        "value": numbers[0] if length == 1 else numbers, "units": "unknown"}
    if key == "boypaused" and value in ("true", "false"):
        return {"kind": "serialized_boolean", "value": value == "true"}
    if re.fullmatch(r"chapter[1-9]\d*", key):
        match = re.fullmatch(r"(data/levels/[^\r\n]+\.branch) ([1-9]\d*)", value)
        if match:
            return {"kind": "chapter_reference", "chapter_number": int(key[7:]),
                    "branch_path": match.group(1), "branch_entry": int(match.group(2)),
                    "resolved": False}
    return None


def decode_readable_records(data, absolute_start=0):
    """Parse simple quoted ASCII assignments, retaining every unknown line.

    No escapes, comments or engine object serialization are assumed. Duplicate
    keys remain separate ordered records; unreadable lines are hashed, not copied.
    """
    records, unknowns = [], []
    pos, decoded_bytes, blank_bytes = 0, 0, 0
    for line_number, line in enumerate(data.splitlines(keepends=True), 1):
        start, end = pos, pos + len(line)
        pos = end
        content = line[:-2] if line.endswith(b"\r\n") else line[:-1] if line.endswith(b"\n") else line
        if not content.strip(b" \t"):
            decoded_bytes += len(line)
            blank_bytes += len(line)
            continue
        match = ASSIGNMENT.fullmatch(content)
        if match is None:
            unknowns.append({"line_number": line_number,
                             **unknown_region(data, start, end, absolute_start)})
            continue
        key, value = (item.decode("ascii") for item in match.groups())
        record = {"index": len(records), "line_number": line_number,
                  "key": key, "value_literal": value,
                  "byte_range": byte_range(start, end, absolute_start),
                  "key_range": byte_range(start + match.start(1), start + match.end(1), absolute_start),
                  "value_range": byte_range(start + match.start(2), start + match.end(2), absolute_start)}
        interpretation = interpreted_value(key, value)
        if interpretation is not None:
            record["interpretation"] = interpretation
        records.append(record)
        decoded_bytes += len(line)
    return {"format": "quoted ASCII assignment records", "sha256": sha256(data),
            "records": records, "unknown_regions": unknowns,
            "coverage": {"member_size": len(data), "bytes_decoded": decoded_bytes,
                         "bytes_undecoded": len(data) - decoded_bytes,
                         "blank_bytes": blank_bytes, "complete": not unknowns,
                         "execution_recovered": False}}


def index_ranges(indices):
    ranges = []
    for index in sorted(indices):
        if ranges and index == ranges[-1][1] + 1:
            ranges[-1][1] = index
        else:
            ranges.append([index, index])
    return ranges


def inspect_package(path, selected, script=False):
    data = path.read_bytes()
    payload_offset, members = decode_package(data)
    missing = set(selected) - set(range(len(members)))
    if missing:
        raise DecodeError(f"selected member indices not present: {sorted(missing)}")
    decoded_members = []
    for index, label in selected.items():
        member = members[index]
        raw = member.read(data)
        decoded = (decode_script if script else decode_readable_records)(raw, member.absolute_start)
        decoded_members.append({"member": member.identity(data), "selection_label": label, **decoded})
    # Union of member ranges: don't assume a table forbids overlap or gaps.
    covered_end = payload_offset
    gaps, overlap_bytes = [], 0
    for member in sorted(members, key=lambda item: item.absolute_start):
        if member.absolute_start > covered_end:
            gaps.append(unknown_region(data, covered_end, member.absolute_start))
        overlap_bytes += max(0, min(covered_end - member.absolute_start, member.size))
        covered_end = max(covered_end, member.absolute_start + member.size)
    if covered_end < len(data):
        gaps.append(unknown_region(data, covered_end, len(data)))
    decoded_bytes = sum(item["coverage"]["bytes_decoded"] for item in decoded_members)
    selected_bytes = sum(members[index].size for index in selected)
    return {"path": str(path), "name": path.name, "size": len(data), "sha256": sha256(data),
            "table": {"layout": "<I count; count * <III (opaque ID, payload-relative offset, size)",
                      "member_count": len(members), "payload_offset": payload_offset,
                      "absolute_start": 0, "absolute_end": payload_offset,
                      "sha256": sha256(data[:payload_offset]), "all_ranges_within_file": True,
                      "last_member_ends_at_eof": covered_end == len(data),
                      "overlap_bytes": overlap_bytes, "gap_regions": gaps},
            "members": decoded_members,
            "coverage": {"table_bytes_decoded": payload_offset,
                         "selected_member_count": len(selected), "selected_member_bytes": selected_bytes,
                         "selected_bytes_decoded": decoded_bytes,
                         "selected_bytes_undecoded": selected_bytes - decoded_bytes,
                         "unselected_member_count": len(members) - len(selected),
                         "unselected_member_index_ranges_inclusive": index_ranges(set(range(len(members))) - set(selected)),
                         "unselected_member_bytes": sum(m.size for m in members if m.index not in selected),
                         "unselected_members_status": "not decoded; no asset extraction"}}


def inspect(root):
    root = Path(root)
    boot = inspect_package(root / "limbo_boot.pkg", SCRIPT_SELECTION, script=True)
    runtime = inspect_package(root / "limbo_runtime.pkg",
                              {i: "chapter map" if i == 0 else "checkpoint records" for i in range(103)})
    defaults = []
    returning_functions = []
    for item in boot["members"]:
        for scope in ("top", "local"):
            for decl in item[f"{scope}_declarations"]:
                if "annotation_default" in decl:
                    defaults.append({"member_index": item["member"]["index"], "declaration_scope": scope,
                                     "name": decl["name"], "annotation": decl["annotation"],
                                     **decl["annotation_default"], "byte_range": decl["byte_range"]})
                signature = decl.get("function_signature", {})
                if signature.get("return_count", 0):
                    returning_functions.append({"member_index": item["member"]["index"],
                                                "name": decl["name"], "signature": signature})
    values = {key: Counter() for key in ("worldgravity", "boygravity", "boydir", "boypaused")}
    exceptional_gravity = []
    for item in runtime["members"][1:]:
        for record in item["records"]:
            key, value = record["key"], record["value_literal"]
            if key in values:
                values[key][value] += 1
            if key == "worldgravity" and value != "0.000000,-10.000000":
                exceptional_gravity.append({"member_index": item["member"]["index"],
                                            "value_literal": value, "byte_range": record["byte_range"]})
    return {"schema_version": SCHEMA_VERSION,
            "method": "Read-only structured byte decoding; no target execution or asset copying.",
            "offset_convention": "All byte ranges are half-open. Absolute offsets are in the package; member offsets start at zero.",
            "packages": [boot, runtime],
            "observations": {"annotation_defaults": defaults,
                             "nonempty_return_type_extensions": returning_functions,
                             "chapter_map_record_count": len(runtime["members"][0]["records"]),
                             "checkpoint_member_count": len(runtime["members"]) - 1,
                             "checkpoint_literal_counts": {key: dict(sorted(counter.items())) for key, counter in values.items()},
                             "nonstandard_checkpoint_worldgravity": exceptional_gravity},
            "inferences": ["The table and declaration layouts fit selected bytes, but are not an official format specification.",
                           "raw_fields[1] == 13 selects the argument-count/type-ID and return-count/type-ID extension.",
                           "Selection labels describe declaration vocabulary, not proven execution or assigned original script filenames."],
            "unknowns": ["Script tails are hashed and explicitly undecoded; executable semantics/control flow were not recovered.",
                         "The meanings of the eleven raw fields and type IDs remain unknown beyond the structural function discriminator.",
                         "Annotation defaults/ranges are serialized declaration metadata, not actual level-instance parameters.",
                         "Checkpoint literals are stored records, not measured state, gravity units, a universal default or proof of behavior.",
                         "Chapter-to-checkpoint mapping, level geometry, water/rope algorithms and runtime timestep remain unresolved.",
                         "Unselected members, compression and engine object serialization were not decoded."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="Caller-supplied LIMBO installation; opened read-only")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Prevent an accidental output overwrite of an input package.
    if args.output.resolve() in {(args.root / name).resolve()
                                 for name in ("limbo_boot.pkg", "limbo_runtime.pkg")}:
        parser.error("output must not overwrite a reference package")
    report = inspect(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    for package in report["packages"]:
        coverage = package["coverage"]
        print(f"{package['name']}: {coverage['selected_member_count']} members, "
              f"{coverage['selected_bytes_decoded']} decoded bytes, "
              f"{coverage['selected_bytes_undecoded']} undecoded selected bytes")
    print("Saved read-only structured findings:", args.output)


if __name__ == "__main__":
    main()
